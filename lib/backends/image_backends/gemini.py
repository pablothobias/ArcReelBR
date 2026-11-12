"""GeminiImageBackend: image-generation logic extracted from GeminiClient."""

from __future__ import annotations

import asyncio
import json as json_module
import logging
from pathlib import Path
from typing import ClassVar

import httpx
from PIL import Image
from pydantic import BaseModel

from arcreel_catalog_core import ImageFacts
from lib.backends.backend_runtime import should_retry_submit
from lib.backends.gemini_shared import (
    VERTEX_SCOPES,
    RateLimiter,
    gemini_http_options,
    get_shared_rate_limiter,
    resolve_gemini_api_key,
    with_retry_async,
)
from lib.backends.image_backends.base import (
    BOTH_IMAGE_CAPABILITIES,
    ImageCapability,
    ImageGenerationRequest,
    ImageGenerationResult,
    ImageRequestFacts,
    ImageResponseError,
    ImageSubmissionAmbiguousError,
)
from lib.backends.providers import PROVIDER_GEMINI
from lib.backends.transport_layer import TransportLayer
from lib.billing.metering import Priced, Usage, price_usage, token_usage
from lib.config.system_config import resolve_vertex_credentials_path
from lib.config.url_utils import normalize_base_url
from lib.infra.async_thread import run_noninterruptible_sync
from lib.infra.image_utils import convert_image_bytes_to_png
from lib.infra.logging_utils import format_kwargs_for_log

logger = logging.getLogger(__name__)

# Default image model.
DEFAULT_IMAGE_MODEL = "gemini-3.1-flash-image"


def _retry_unsent(exc: Exception) -> bool:
    return isinstance(exc, httpx.RequestError) and should_retry_submit(exc)


def _count(value: object) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else None


def _modality_counts(details: object) -> dict[str, int]:
    if not isinstance(details, list):
        return {}
    counts: dict[str, int] = {}
    for item in details:
        modality = getattr(item, "modality", None)
        count = _count(getattr(item, "token_count", None))
        if isinstance(modality, str) and count is not None:
            counts[modality] = counts.get(modality, 0) + count
    return counts


class GeminiImageBackend:
    """Gemini image backend supporting AI Studio and Vertex AI."""

    CHANNEL_CAPABILITIES: ClassVar[frozenset[ImageCapability]] = BOTH_IMAGE_CAPABILITIES
    # Channels impose no reference-count limit; generation-specific Gemini image maxima are model-entry facts.
    CHANNEL_REFERENCE_LIMIT: ClassVar[int | None] = None

    def __init__(
        self,
        *,
        backend_type: str = "aistudio",
        api_key: str | None = None,
        rate_limiter: RateLimiter | None = None,
        image_model: str | None = None,
        base_url: str | None = None,
        credentials_path: str | None = None,
        transport_layer: TransportLayer | None = None,
    ):
        from google import genai as _genai
        from google.genai import types as _types

        self._types = _types
        self._rate_limiter = rate_limiter or get_shared_rate_limiter()
        self._backend_type = backend_type.strip().lower()
        self._image_model = image_model or DEFAULT_IMAGE_MODEL

        if self._backend_type == "vertex":
            from google.oauth2 import service_account

            credentials_file: Path | None = None
            credentials_file = Path(credentials_path) if credentials_path else resolve_vertex_credentials_path()

            if credentials_file is None:
                raise ValueError("Vertex AI credentials file not found")

            with open(credentials_file, encoding="utf-8") as f:
                creds_data = json_module.load(f)
            project_id = creds_data.get("project_id")

            credentials = service_account.Credentials.from_service_account_file(
                str(credentials_file), scopes=VERTEX_SCOPES
            )

            self._client = _genai.Client(
                vertexai=True,
                project=project_id,
                location="global",
                credentials=credentials,
                http_options=gemini_http_options(None, transport_layer, non_idempotent=True),
            )
        else:
            api_key = resolve_gemini_api_key(api_key)
            effective_base_url = normalize_base_url(base_url)
            self._client = _genai.Client(
                api_key=api_key,
                http_options=gemini_http_options(effective_base_url, transport_layer, non_idempotent=True),
            )

    @property
    def name(self) -> str:
        return f"gemini-{self._backend_type}"

    @property
    def model(self) -> str:
        return self._image_model

    @property
    def capabilities(self) -> set[ImageCapability]:
        return set(self.CHANNEL_CAPABILITIES)

    async def reference_image_limit(self) -> int | None:
        return self.CHANNEL_REFERENCE_LIMIT

    @staticmethod
    def _usage(image_size: str | None) -> Usage:
        """Request facts lack input and non-image output quantities; image-only prices are incomplete."""
        return Usage(
            dimensions={"resolution": image_size} if image_size is not None else {},
            missing_quantities=frozenset({"uncached_input_tokens", "output_tokens", "image_output_tokens"}),
        )

    @staticmethod
    def estimate_usage(facts: ImageRequestFacts) -> Usage:
        entry = facts.entry
        bounds = entry.facts if entry is not None and isinstance(entry.facts, ImageFacts) else None
        if entry is None or bounds is None or bounds.max_input_tokens is None or bounds.max_output_tokens is None:
            return GeminiImageBackend._usage(facts.image_size)
        table = entry.price
        # A nonmonotonic context-dependent table cannot be bounded from the largest context alone.
        if table is None or any("context_tier" in meter.dims for meter in table.meters):
            return GeminiImageBackend._usage(facts.image_size)
        endpoints = []
        for image_output in (0, bounds.max_output_tokens):
            quantities = {
                "uncached_input_tokens": bounds.max_input_tokens,
                "image_output_tokens": image_output,
                "output_tokens": bounds.max_output_tokens - image_output,
            }
            if facts.reference_count is not None:
                quantities["input_images"] = facts.reference_count
            usage = Usage(
                quantities=quantities,
                dimensions={"resolution": facts.image_size} if facts.image_size is not None else {},
                estimate_basis="full_context_output_upper_bound",
            )
            cost = price_usage(table, usage, multiplier=1, estimate=True)
            if not isinstance(cost, Priced):
                return GeminiImageBackend._usage(facts.image_size)
            endpoints.append((cost.amount, usage))
        return max(endpoints, key=lambda endpoint: endpoint[0])[1]

    @with_retry_async(max_attempts=5, backoff_seconds=(2, 4, 8, 16, 32), retry_if=_retry_unsent)
    async def generate(self, request: ImageGenerationRequest) -> ImageGenerationResult:
        """Generate images asynchronously."""
        # 1. Rate limiting.
        if self._rate_limiter:
            await self._rate_limiter.acquire_async(self._image_model)

        # 2. Assemble contents: reference images first in array order, prompt last.
        #    Reference_Images prompt declarations identify images as 图N; insert no text labels between images.
        refs = request.reference_images
        # Opening/decoding references blocks I/O; offload individually and await concurrently without blocking event loops.
        contents: list = await asyncio.gather(*[asyncio.to_thread(self._load_image_detached, ref.path) for ref in refs])
        contents.append(request.prompt)

        image_config_kwargs: dict = {"aspect_ratio": request.aspect_ratio}
        if request.image_size is not None:
            image_config_kwargs["image_size"] = request.image_size

        config = self._types.GenerateContentConfig(
            response_modalities=["IMAGE"],
            candidate_count=1,
            automatic_function_calling=self._types.AutomaticFunctionCallingConfig(disable=True),
            image_config=self._types.ImageConfig(**image_config_kwargs),
            max_output_tokens=request.max_output_tokens,
        )

        # 4. Call asynchronous API.
        logger.info(
            "调用 %s 图片 SDK payload=%s",
            self.name,
            format_kwargs_for_log(
                {"model": self._image_model, "contents": contents, "image_config": image_config_kwargs}
            ),
        )
        try:
            response = await self._client.aio.models.generate_content(
                model=self._image_model, contents=contents, config=config
            )
        except (TimeoutError, httpx.RequestError) as exc:
            if _retry_unsent(exc) or isinstance(exc, (httpx.LocalProtocolError, httpx.UnsupportedProtocol)):
                raise
            raise ImageSubmissionAmbiguousError(
                provider=self.name, result=self._measured_result(None, request)
            ) from exc

        # 5. Parse responses/save.
        # Providers returned: decoding/persistence cannot be interrupted by cancellation, per backend.md postresponse accounting rules.
        result = self._measured_result(response, request)
        try:
            await run_noninterruptible_sync(self._process_image_response, response, request.output_path)
        except Exception as exc:
            raise ImageResponseError(str(exc), result=result) from exc
        return result

    def _measured_result(self, response, request: ImageGenerationRequest) -> ImageGenerationResult:
        metadata = getattr(response, "usage_metadata", None)
        prompt = _count(getattr(metadata, "prompt_token_count", None))
        cached = _count(getattr(metadata, "cached_content_token_count", None))
        candidates = _count(getattr(metadata, "candidates_token_count", None))
        thoughts = _count(getattr(metadata, "thoughts_token_count", None))
        total = _count(getattr(metadata, "total_token_count", None))
        tool_input = _count(getattr(metadata, "tool_use_prompt_token_count", None))
        # Requests carry no tools; a consistent total can prove an omitted thought quantity.
        if thoughts is None and total is not None and prompt is not None and candidates is not None:
            residual = total - prompt - candidates
            if residual >= 0 and tool_input in (None, 0):
                thoughts = residual
        outputs = _modality_counts(getattr(metadata, "candidates_tokens_details", None))
        inputs = _modality_counts(getattr(metadata, "prompt_tokens_details", None))
        image_tokens = outputs.get("IMAGE")
        # A zero candidate total proves there are no response-image tokens; missing details otherwise remain unknown.
        if image_tokens is None and candidates == 0:
            image_tokens = 0
        text_tokens = (
            candidates - image_tokens + thoughts
            if candidates is not None
            and image_tokens is not None
            and thoughts is not None
            and candidates >= image_tokens
            else None
        )
        quantities = token_usage(input_tokens=prompt, output_tokens=text_tokens, cache_read_tokens=cached)
        if image_tokens is not None:
            quantities["image_output_tokens"] = image_tokens
        missing = {"uncached_input_tokens", "output_tokens", "image_output_tokens"} - quantities.keys()
        if prompt is not None and cached is not None and cached > prompt:
            missing.add("uncached_input_tokens")
        if candidates is not None and sum(outputs.values()) > candidates:
            missing.update({"output_tokens", "image_output_tokens"})
        if tool_input or (
            total is not None
            and prompt is not None
            and candidates is not None
            and thoughts is not None
            and total != prompt + candidates + thoughts
        ):
            missing.update({"uncached_input_tokens", "output_tokens", "image_output_tokens"})
        return ImageGenerationResult(
            image_path=request.output_path,
            provider=PROVIDER_GEMINI,
            model=self._image_model,
            usage_tokens=total,
            input_tokens=prompt,
            output_tokens=candidates + thoughts if candidates is not None and thoughts is not None else None,
            cache_read_tokens=cached,
            provider_response={"usage_metadata": metadata.model_dump(mode="json", exclude_none=True)}
            if isinstance(metadata, BaseModel)
            else None,
            image_input_tokens=inputs.get("IMAGE") if sum(inputs.values()) == prompt else None,
            text_input_tokens=inputs.get("TEXT") if sum(inputs.values()) == prompt else None,
            image_output_tokens=image_tokens if text_tokens is not None else None,
            text_output_tokens=text_tokens,
            usage=Usage(
                quantities=quantities,
                dimensions={"resolution": request.image_size} if request.image_size is not None else {},
                missing_quantities=frozenset(missing),
            ),
        )

    @staticmethod
    def _load_image_detached(image_path: str | Path) -> Image.Image:
        """Load images from paths, detaching underlying file handles."""
        with Image.open(image_path) as img:
            return img.copy()

    @staticmethod
    def _process_image_response(response, output_path: Path) -> None:
        """Decode returned image bytes and persist the canonical PNG artifact."""
        for part in response.parts:
            if part.inline_data is not None:
                content = convert_image_bytes_to_png(part.inline_data.data)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                output_path.write_bytes(content)
                return
        raise RuntimeError("The API returned no image")
