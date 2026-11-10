"""Client media ingest: original product photographs, finished media, storyboard end frames and project BGM."""

from server.agent_toolset.declaration import BLOCKED, READ_CHECK, ToolDeclaration
from server.media_tools.media_ingest import (
    ArrangeProductReferenceImagesRequest,
    ClearEndFrameRequest,
    InstallFinishedMediaRequest,
    ProductReferenceRequest,
    SetEndFrameRequest,
    UploadBgmRequest,
    UploadProductReferenceImagesRequest,
    arrange_product_reference_images_tool,
    clear_end_frame_tool,
    install_finished_media,
    list_product_reference_images,
    product_reference_summary,
    set_end_frame,
    upload_bgm,
    upload_product_reference_images,
)

_BYTES_NOTE = (
    "Bytes come from the client as content_base64 (≤20 MiB base64) or a completed staged_upload_id; "
    "server paths are never accepted. No generation task or provider call is made."
)

UPLOAD_PRODUCT_REFERENCE_IMAGES = ToolDeclaration(
    name="upload_product_reference_images",
    description=(
        "Append real product photographs to an existing product's original reference_images, in the given order, "
        "with the exact bytes preserved (sha256 returned per photo). All photos are validated before any is written; "
        "a failed batch leaves no files. Originals are not the product_sheet: on the storyboard route the sheet and "
        "all originals are sent; on the reference-video route a declared sheet replaces the originals. " + _BYTES_NOTE
    ),
    request_model=UploadProductReferenceImagesRequest,
    migration=BLOCKED,
    domain_key="product_reference_images",
    handler=upload_product_reference_images,
    summary=product_reference_summary,
)

LIST_PRODUCT_REFERENCE_IMAGES = ToolDeclaration(
    name="list_product_reference_images",
    description=(
        "Read a product's original photographs (order, ref_id, sha256, presence), its product_sheet state, and which "
        "images the current route actually sends before per-request clamping. Read-only."
    ),
    request_model=ProductReferenceRequest,
    migration=READ_CHECK,
    domain_key="product_reference_images",
    handler=list_product_reference_images,
    summary=product_reference_summary,
)

ARRANGE_PRODUCT_REFERENCE_IMAGES = ToolDeclaration(
    name="arrange_product_reference_images",
    description=(
        "The dedicated native transaction for a product's original reference_images (the same project-lock write "
        "as the Web product edit): reorder, or detach photos. Pass expected_order from list_product_reference_images; "
        "a concurrent change is refused with reference_images_changed. Detaching any photo requires "
        "confirm_detach=true after the user approves (otherwise confirmation_required lists them); detached photos "
        "keep their files. Other product fields are untouched; brand stays outside Agent writes. No generation."
    ),
    request_model=ArrangeProductReferenceImagesRequest,
    migration=BLOCKED,
    domain_key="product_reference_images",
    handler=arrange_product_reference_images_tool,
    summary=product_reference_summary,
)

INSTALL_FINISHED_MEDIA = ToolDeclaration(
    name="install_finished_media",
    description=(
        "Install user-approved finished media as the selected manual_upload version through the native upload "
        "transaction: asset sheet (character/scene/prop/product), character derivative sheet, storyboard image or "
        "storyboard video (storyboard route), or reference-video unit video. Version history, manifest claim and "
        "dependent stale state are preserved. Not a character reference upload (use upload_reference) and not "
        "generation. Images are normalized natively (sheets/storyboards may be re-encoded); videos keep their bytes. "
        + _BYTES_NOTE
    ),
    request_model=InstallFinishedMediaRequest,
    migration=BLOCKED,
    domain_key="installed_media",
    handler=install_finished_media,
)

SET_END_FRAME = ToolDeclaration(
    name="set_end_frame",
    description=(
        "Set a storyboard-route shot's end frame from client bytes or an existing project image identity; a PNG "
        "snapshot is copied so later source changes do not alter it. Refused (end_frame_unsupported_by_video_model) "
        "when the project's video model does not send last frames, since generation would silently ignore it — "
        "stricter than the Web editor — and on the reference-video route. patch_episode_script cannot write end_frame_image. "
        + _BYTES_NOTE
    ),
    request_model=SetEndFrameRequest,
    migration=BLOCKED,
    domain_key="end_frame",
    handler=set_end_frame,
)

CLEAR_END_FRAME = ToolDeclaration(
    name="clear_end_frame",
    description=(
        "Clear a storyboard-route shot's end frame: the snapshot moves to project trash and the field is cleared."
    ),
    request_model=ClearEndFrameRequest,
    migration=BLOCKED,
    domain_key="end_frame",
    handler=clear_end_frame_tool,
)

UPLOAD_BGM = ToolDeclaration(
    name="upload_bgm",
    description=(
        "Add user-supplied music to the project BGM library: native audio validation, duration probe and loudness "
        "measurement (gain to -16 LUFS), returning BGM id, duration, gain and digest. Does not insert it into any "
        "timeline; use edit_timeline insert_bgm separately when authorized. " + _BYTES_NOTE
    ),
    request_model=UploadBgmRequest,
    migration=BLOCKED,
    domain_key="bgm",
    handler=upload_bgm,
)

MEDIA_INGEST_TOOLS = (
    UPLOAD_PRODUCT_REFERENCE_IMAGES,
    LIST_PRODUCT_REFERENCE_IMAGES,
    ARRANGE_PRODUCT_REFERENCE_IMAGES,
    INSTALL_FINISHED_MEDIA,
    SET_END_FRAME,
    CLEAR_END_FRAME,
    UPLOAD_BGM,
)
