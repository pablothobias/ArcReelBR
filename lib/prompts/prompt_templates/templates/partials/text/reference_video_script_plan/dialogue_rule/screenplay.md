- Write the author’s dialogue as dialogue tokens (`@[character]{dialogue}`), and off-screen speech / narration as off-screen speech tokens (`{dialogue}`), **copying verbatim**:
  do not rewrite, polish, remove, or add content. Generic extras (old man A / several villagers) are not registered characters; write their dialogue as off-screen speech tokens,
  and identify the speaker in the visual description. Dialogue is part of the content contract and will not be changed by prompt_authoring.
- Convert visible action in camera directions, shot sizes, and stage directions into visual descriptions; strip formatting symbols (Markdown, △, all kinds of tags, tables, emoji).
  The author’s explicit framing, camera movement, and blocking are source-backed direction: keep them in the body (see the body-writing guide) rather than dropping them; an author’s cut starts a new unit when the duration rules allow it (see the body-writing guide).
