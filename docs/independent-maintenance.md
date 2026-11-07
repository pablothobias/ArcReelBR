# ArcReelBR independent maintenance

ArcReelBR is maintained at https://github.com/pablothobias/ArcReelBR. The original Git history, licenses and attribution remain intact. `origin` points to this repository; no `upstream` remote is required.

## Local operation

Both Compose configurations build `arcreelbr:local` from this checkout (`deploy/..` or `deploy/production/../..`). `pull_policy: build` prevents a registry application image from replacing the local customizations. Run `docker compose up -d` from the appropriate deployment directory after preparing its `.env`. Existing service names, mounts, authentication and database settings are unchanged. Upgrades require updating this checkout and rebuilding. No local projects are migrated by this configuration change.

Application update checks and the About link target ArcReelBR. Until this repository publishes a release, GitHub's latest-release endpoint returns 404 and the UI reports that the update check could not complete. This does not prevent local operation.

Install only the public connection skills with:

```bash
npx skills add pablothobias/ArcReelBR --skill setup-arcreel-skills video-workflow
```

The documentation site defaults to `http://localhost:3000/`. Set `DOCS_URL` and, if needed, `DOCS_BASE_URL` only when choosing your own hosting destination. Editing links target this repository. No documentation site was deployed.

## Manual integrations

All workflow roots use `workflow_dispatch`. Reusable workflows retain `workflow_call`; no push, PR, tag or schedule starts a workflow in this repository.

- `sync-public-skills.yml` packages the two public connection skills and `adapt-custom-endpoint` into an artifact. It never pushes to an external skills repository.
- Market validation/publication workflows use ArcReelBR tooling. They skip execution in the application repository because it is not a market source. They remain reusable by a separately configured market repository.
- `release-please.yml` uses this repository's `GITHUB_TOKEN` by default. An optional GitHub App must be installed on your repository; both `RELEASE_PLEASE_APP_CLIENT_ID` and `RELEASE_PLEASE_APP_PRIVATE_KEY` are needed. Without an App, GitHub must allow Actions to create PRs before using this optional release workflow. No such permission expansion was made during this audit.
- Release PRs keep the checked-in model-catalog snapshot unless you explicitly set the `CATALOG_BASE_URL` repository variable. Docker releases never dispatch a build in the original catalog repository.
- Docker image publishing remains optional and manual. GHCR coordinates derive from `github.repository`. Docker Hub publishing/description synchronization require your own `DOCKERHUB_USERNAME` and `DOCKERHUB_TOKEN` for `pablothobias/arcreelbr`; those credentials and a registry release are not needed for local builds.
- Project synchronization is skipped until `PROJECT_STATUS_PROJECT_ID`, `PROJECT_STATUS_FIELD_ID` and `PROJECT_STATUS_OPTIONS` repository variables are configured. The last value is a JSON object mapping `Inbox`, `Needs info`, `Ready · agent`, `Ready · human`, `In progress`, `In review` and `Done` to the chosen board's option IDs. Set `PROJECT_STATUS_SYNC_TOKEN` with access to that board. The script defaults to `pablothobias/ArcReelBR`, or uses `GITHUB_REPOSITORY`, and queries the configured Project node directly, supporting personal and organization boards. Missing or malformed configuration fails before network requests. No original board IDs are retained.

## Intentional external references

These are dependencies or attribution, not repository ownership or publication targets:

- Official model-catalog reads from `ArcReel/arcreel-catalog`, including the checked-in snapshot. Local operation already has a snapshot; this audit does not change model availability, update policy or minimum-version contracts.
- The optional official marketplace source `ArcReel/arcreel-market`, its contribution links and the official marketplace service at `arc-reel.com`. These preserve existing browsing, sharing and feedback features; they do not publish ArcReelBR releases or code.
- Provider endpoints, including `api.arc-reel.com`, which remain selectable integrations rather than a hosting destination for this repository.
- Original documentation, community, sponsorship and commercial licensing references in the inherited README, third-party dependencies, `NOTICE`, changelog and historical research. The README identifies those contacts and documentation as belonging to the original project. They do not imply ArcReelBR support from upstream.

GitHub Issues is enabled for ArcReelBR. The inherited homepage pointing to the original product was cleared. No workflows, media generation, deployments, releases or Project mutations were run during this audit.
