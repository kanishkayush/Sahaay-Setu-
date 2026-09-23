import type { LanguageCode } from '@/api/contracts';

/**
 * App language → BCP-47 tag for speech engines.
 *
 * All six are the Indian variants deliberately. `hi` alone gets a speaker
 * trained on a different register, and `en` alone gets a US voice that
 * mispronounces every rupee figure and place name in the app — "Tiruchirappalli"
 * and "lakh" are the obvious ones. `en-IN` is the correct choice even for the
 * English UI, because the content is Indian regardless of interface language.
 */
export const SPEECH_LOCALE: Record<LanguageCode, string> = {
  en: 'en-IN',
  hi: 'hi-IN',
  mr: 'mr-IN',
  bn: 'bn-IN',
  ta: 'ta-IN',
  te: 'te-IN',
};

export function speechLocaleFor(language: LanguageCode): string {
  return SPEECH_LOCALE[language] ?? 'en-IN';
}
