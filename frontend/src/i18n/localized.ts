import type { LanguageCode, LocalizedText } from '@/api/contracts';

/**
 * Backend content (scheme names, eligibility labels) arrives as a
 * `LocalizedText` map rather than an i18n key, because the catalogue is data,
 * not UI copy. Always read it through here so the English fallback is applied
 * consistently.
 */
export function pickLocalized(
  text: LocalizedText | undefined,
  language: LanguageCode,
  fallback = '',
): string {
  if (!text) return fallback;
  return text[language] ?? text.en ?? fallback;
}
