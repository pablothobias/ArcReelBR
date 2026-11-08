// Brand configuration: single source of truth for product naming and owner-supplied metadata.
// Override at build time via Vite env vars
// (VITE_BRAND_NAME / VITE_BRAND_TAGLINE / VITE_BRAND_DESCRIPTION).
//
// Source code references BRAND.name (or the [[brand]] placeholder in i18n
// resources) so the displayed product name is not hardcoded across files.
// Defaults identify this distribution; downstream distributions can override
// via frontend/.env without code changes.

const env = import.meta.env as Record<string, string | undefined>;

function fallback(value: string | undefined, defaultValue: string): string {
  // Trim + empty check so VITE_BRAND_NAME="" (or whitespace) falls back to the
  // default when the override is blank.
  if (typeof value !== "string") return defaultValue;
  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : defaultValue;
}

export const BRAND = {
  name: fallback(env.VITE_BRAND_NAME, "RafaCena"),
  tagline: fallback(env.VITE_BRAND_TAGLINE, "Agent-powered AI video creation workspace"),
  description: fallback(
    env.VITE_BRAND_DESCRIPTION,
    "An AI video creation workspace for projects, scripts, storyboards, video generation and Agent conversations.",
  ),
} as const;

export const BRAND_DOCUMENT_TITLE = `${BRAND.name} · ${BRAND.tagline}`;

