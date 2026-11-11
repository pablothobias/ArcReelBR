---
status: accepted
---

# English reference-video prompt markers

Reference-video prompts bind subjects and voices to request inputs with positional markers. They used the Chinese literals `@图片N` / `@音频N`, joined with `、` and ended with `。`. These markers now use the English form that Seedance documents: `@Image N` / `@Audio N`, joined with `, ` and ended with `.`. For example: `<Caio>@Image 1, <Marlene>@Image 2.` Numbering is unchanged: it counts the Nth sent reference image and the Nth reference-audio clip, separately, from 1.

ADR 0121 preserves "syntax recognized by code". These markers are not such syntax. No ArcReel code parses them, and no provider documents the Chinese literals as required. Checked on 2026-11-11:

- **Seedance:** documents English labels. The BytePlus guide shows `@Image 1` / `@Audio 1` and `<Subject_N>@<Image_N>`. Its tutorial requires "asset type + number" per type. The Volcengine example itself writes `@图像1`, not `@图片1`. The guide also asks not to mix Chinese and English in dialogue, which the Chinese markers did inside English or Portuguese prompts.
- **Wan 2.7/3.0:** documents "Image 1" for English prompts.
- **Gemini/Veo, Kling, Vidu and MiniMax:** use separate request fields or their own syntax (`<<<image_1>>>`, `@1`, typed `content[]` roles). Neither form is native to them.

## Considered options

- **Per-provider marker dialects.** Rejected. Both Seedance and Wan accept English, so a per-channel capability would add schema, resolver and test surface without changing any outcome.
- **Provider-native syntax per backend** (Kling `<<<image_1>>>`, Vidu `@1`, Wan 2.6 `character1`). Possibly better binding for those models, but it is a separate change with its own evidence. Not decided here.

## Consequences

- Jobs submitted before the change resume with their stored prompt (`resume_executor` replays the checkpoint prompt). Their captured-submission preview keeps showing `@图片N`.
- Reference-video staleness bases project unit text and sent images, not the rendered prompt, so existing videos stay current.
- Prompts grow by 4 characters per marker and 1 per binding joiner (`、` → `, `). Prompt-length limits (`gate_video_request`, Vidu `/reference2video`) still reject before any provider call.
- Storyboard and grid image prompts keep their `图N` labels. Those labels are part of the storyboard-image staleness basis, so changing them would make existing images stale. They need their own decision.
