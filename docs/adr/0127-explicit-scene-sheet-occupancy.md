---
status: accepted
---

# Explicit scene-sheet occupancy

Scene sheets are empty environment references by default: the guard says no people appear and `Avoid:` excludes people in the shot ([ADR 0066](0066-asset-sheet-layout-by-consumer.md)). Some scenes are defined by their occupants, such as a classroom of seated adults watching in silence. Their descriptions then contradicted the fixed wrappers, and the only workaround was a manual image edit or a finished-image upload.

A scene entry now has an optional `occupancy` field: `"empty"` or `"occupied"`. If the field is absent or `""`, the scene is empty. `"occupied"` replaces the guard with "show only the people the description asks for, as anonymous occupants … no distinctive faces or close-ups". It also replaces the people exclusion with "people beyond those described, close-ups of faces". This narrows ADR 0066's scene guard to the default case only. For an empty scene, people remain identity-irrelevant to the reference and stay excluded.

Occupancy is an author's choice. It is never inferred from description wording, source text, genre or locale. Word matching cannot separate "a classroom that once held students" from "a classroom full of students". It would also silently change the sheets of existing projects.

## Surface

- **Schema:** `AssetSpec.choice_fields` declares closed-vocabulary fields. The first value is the default, and an absent field means that default. The project validator rejects other values, which also covers Agent writes: `upsert_assets` refuses any write that adds a validation error.
- **Writes:** `occupancy` is writable through REST create/PATCH, where an unknown value returns 422. The Agent writes it through `patch_project` (`agent_editable_extra_fields`). The skill tells the Agent to set it only on an explicit user request.
- **Prompt:** the `asset/sheet` template takes a boolean `occupied` slot. The template engine allows only truthiness conditions. Only the scene guard and the scene exclusion partials read it.
- **Freshness:** the asset-sheet basis adds `asset.occupancy` only when it is `"occupied"`. Absent and empty scenes keep their digests byte for byte, so existing sheets stay current without a migration. Toggling occupancy makes the current sheet stale, and toggling back makes it current again.
- **UI:** the scene editor has a "People in asset sheet" switch, which is saved with the description in the same edit unit.

## Considered options

- **Infer occupancy from the description.** Rejected for the reasons above.
- **A free-text people description separate from `description`.** Rejected. The description already carries the scene's content, and a second field would duplicate the source of truth for what appears in the image.
- **A per-generation flag instead of a stored field.** Rejected. The freshness basis must be derivable from project state, and a generation-time flag would make the same sheet's currency depend on how it was last requested.

## Consequences

- The global asset library stores description and image only. A scene copied into or out of the library arrives with the default occupancy, and its sheet arrives as an uploaded image whose basis is the image bytes. Its currency is therefore unaffected.
- An occupied scene sheet sent as a reference may carry its occupants into storyboard images and videos. Authors opt in knowing that. The empty default remains the recommended choice for scenes that characters move through.
- Model compliance with the occupied wording (anonymity, no close-ups) is unverified until a generation is run.
