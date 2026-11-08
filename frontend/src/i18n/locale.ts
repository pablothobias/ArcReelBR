export const SUPPORTED_LANGUAGES = ['zh', 'en', 'vi', 'ru'] as const;
export type SupportedLanguage = typeof SUPPORTED_LANGUAGES[number];
export const DEFAULT_LANGUAGE: SupportedLanguage = 'en';

/** Normalize regional locale preferences without treating unsupported values as a saved choice. */
export function supportedLanguage(value: string | null | undefined): SupportedLanguage | undefined {
  const base = value?.trim().toLowerCase().split(/[-_]/)[0];
  return SUPPORTED_LANGUAGES.find((language) => language === base);
}

export function normalizeLanguage(value: string | null | undefined): SupportedLanguage {
  return supportedLanguage(value) ?? DEFAULT_LANGUAGE;
}
