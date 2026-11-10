"""Typed media selectors: one discriminated model per media kind, addressed by native identities only.

A selector names a project object (asset, storyboard item, video unit, grid, timeline, BGM, task, package) and,
where the native store keeps version history, an optional version. It never carries a filesystem path."""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictInt, TypeAdapter

_VERSION_DESCRIPTION = "Version number from the native version history; omit to use the current version"


class _Selector(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class AssetSheetSelector(_Selector):
    kind: Literal["asset_sheet"]
    asset_type: Literal["character", "scene", "prop", "product"] = Field(description="Asset type")
    name: str = Field(min_length=1, max_length=200, description="Asset name")
    version: StrictInt | None = Field(default=None, ge=1, description=_VERSION_DESCRIPTION)


class CharacterDerivativeSelector(_Selector):
    kind: Literal["character_derivative"]
    name: str = Field(min_length=3, max_length=400, description="Derivative ID in base-name/derivative-name form")
    version: StrictInt | None = Field(default=None, ge=1, description=_VERSION_DESCRIPTION)


class ProductReferenceImageSelector(_Selector):
    kind: Literal["product_reference_image"]
    product: str = Field(min_length=1, max_length=200, description="Product asset name")
    index: StrictInt = Field(ge=0, description="Zero-based position in the product's reference_images list")


class CharacterReferenceImageSelector(_Selector):
    kind: Literal["character_reference_image"]
    character: str = Field(
        min_length=1, max_length=200, description="Character name whose uploaded reference image to read"
    )


class StyleImageSelector(_Selector):
    kind: Literal["style_image"]


class CharacterVoiceReferenceSelector(_Selector):
    kind: Literal["character_voice_reference"]
    character: str = Field(
        min_length=1, max_length=200, description="Character name whose bound reference audio to read"
    )


class VoiceSampleSelector(_Selector):
    kind: Literal["voice_sample"]
    task_id: str = Field(min_length=1, max_length=128, description="Task ID of a succeeded voice_sample task")


class StoryboardImageSelector(_Selector):
    kind: Literal["storyboard_image"]
    script: str = Field(min_length=1, max_length=255, description="Script filename, for example episode_1.json")
    item_id: str = Field(min_length=1, max_length=128, description="Storyboard ID (segment_id / scene_id)")
    version: StrictInt | None = Field(default=None, ge=1, description=_VERSION_DESCRIPTION)


class EndFrameSelector(_Selector):
    kind: Literal["end_frame"]
    script: str = Field(min_length=1, max_length=255, description="Script filename, for example episode_1.json")
    item_id: str = Field(min_length=1, max_length=128, description="Storyboard ID carrying the end frame")
    version: StrictInt | None = Field(default=None, ge=1, description=_VERSION_DESCRIPTION)


class GridCompositeSelector(_Selector):
    kind: Literal["grid_composite"]
    grid_id: str = Field(pattern=r"^grid_[0-9a-f]{12}$", description="Grid ID, for example grid_0123456789ab")
    version: StrictInt | None = Field(default=None, ge=1, description=_VERSION_DESCRIPTION)


class NarrationAudioSelector(_Selector):
    kind: Literal["narration_audio"]
    unit_id: str = Field(min_length=1, max_length=128, description="Unit (segment) ID whose narration audio to read")
    version: StrictInt | None = Field(default=None, ge=1, description=_VERSION_DESCRIPTION)


class UnitVideoSelector(_Selector):
    kind: Literal["unit_video"]
    script: str = Field(min_length=1, max_length=255, description="Script filename, for example episode_1.json")
    unit_id: str = Field(
        min_length=1,
        max_length=128,
        description="Video-unit ID: storyboard ID for storyboard-to-video, unit_id for reference-to-video",
    )
    version: StrictInt | None = Field(default=None, ge=1, description=_VERSION_DESCRIPTION)


class FinalCutSelector(_Selector):
    kind: Literal["final_cut"]
    timeline: str = Field(min_length=1, max_length=128, description="Edit timeline ID whose rendered final cut to read")
    narration: Literal["with_narration", "without_narration"] | None = Field(
        default=None, description="Narration variant; omit to use the project default"
    )
    subtitles: Literal["burned_subtitles", "no_subtitles"] | None = Field(
        default=None, description="Subtitle mode; omit to use the project default"
    )


class JianyingPackageSelector(_Selector):
    kind: Literal["jianying_package"]
    package_id: str = Field(pattern=r"^[0-9a-f]{32}$", description="Package ID returned by prepare_jianying_package")


class BgmSelector(_Selector):
    kind: Literal["bgm"]
    bgm_id: str = Field(pattern=r"^bgm-[0-9a-f]{8}$", description="BGM ID from list_bgm")


type MediaSelector = Annotated[
    AssetSheetSelector
    | CharacterDerivativeSelector
    | ProductReferenceImageSelector
    | CharacterReferenceImageSelector
    | StyleImageSelector
    | CharacterVoiceReferenceSelector
    | VoiceSampleSelector
    | StoryboardImageSelector
    | EndFrameSelector
    | GridCompositeSelector
    | NarrationAudioSelector
    | UnitVideoSelector
    | FinalCutSelector
    | JianyingPackageSelector
    | BgmSelector,
    Field(discriminator="kind"),
]

MEDIA_KINDS: tuple[str, ...] = (
    "asset_sheet",
    "character_derivative",
    "product_reference_image",
    "character_reference_image",
    "style_image",
    "character_voice_reference",
    "voice_sample",
    "storyboard_image",
    "end_frame",
    "grid_composite",
    "narration_audio",
    "unit_video",
    "final_cut",
    "jianying_package",
    "bgm",
)

_ADAPTER: TypeAdapter[Any] = TypeAdapter(MediaSelector)


def parse_selector(value: Any) -> Any:
    """Validate a raw selector mapping; raises ``pydantic.ValidationError``."""
    return _ADAPTER.validate_python(value)


def selector_payload(selector: Any) -> dict[str, Any]:
    """Canonical JSON form: every field, including ``None`` defaults, so equal selectors serialize identically."""
    return selector.model_dump(mode="json")


__all__ = [
    "MEDIA_KINDS",
    "AssetSheetSelector",
    "BgmSelector",
    "CharacterDerivativeSelector",
    "CharacterReferenceImageSelector",
    "CharacterVoiceReferenceSelector",
    "EndFrameSelector",
    "FinalCutSelector",
    "GridCompositeSelector",
    "JianyingPackageSelector",
    "MediaSelector",
    "NarrationAudioSelector",
    "ProductReferenceImageSelector",
    "StoryboardImageSelector",
    "StyleImageSelector",
    "UnitVideoSelector",
    "VoiceSampleSelector",
    "parse_selector",
    "selector_payload",
]
