# ArcReelBR skills

Install the public Agent skills directly from this repository:

```bash
npx skills add pablothobias/ArcReelBR --skill setup-arcreel-skills video-workflow
```

This directory is the source of truth for `setup-arcreel-skills` and `video-workflow`, licensed under the [MIT License](LICENSE). The embedded Agent also uses `adapt-custom-endpoint`, whose source is `agent_runtime_profile/.claude/skills/adapt-custom-endpoint/`.

The manual `sync-public-skills.yml` workflow packages all three skills as a downloadable artifact. It does not push to a separate distribution repository.
