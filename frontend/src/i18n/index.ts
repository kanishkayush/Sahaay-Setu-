import AsyncStorage from '@react-native-async-storage/async-storage';
import * as Localization from 'expo-localization';
import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';

import type { LanguageCode } from '@/api/contracts';
import bn from './locales/bn.json';
import en from './locales/en.json';
import hi from './locales/hi.json';
import mr from './locales/mr.json';
import ta from './locales/ta.json';
import te from './locales/te.json';

/**
 * Multilingual setup.
 *
 * Design rules for this project:
 *  - `en` is the fallback for EVERY key. A partially translated locale is fine;
 *    a missing string must never render as a raw key.
 *  - The chosen language persists on-device and is sent to the backend on every
 *    assistant/recommendation call as `language` / `responseLanguage`, so the
 *    AI answers in the same language the UI is in.
 *  - Adding a language = drop a JSON file in `locales/`, add it to
 *    `SUPPORTED_LANGUAGES` and to `LanguageCodeSchema` in the API contract.
 */

export const STORAGE_KEY_LANGUAGE = 'sahaay.language';

export type LanguageOption = {
  code: LanguageCode;
  /** Name written in that language — never translate this. */
  endonym: string;
  englishName: string;
};

export const SUPPORTED_LANGUAGES: LanguageOption[] = [
  { code: 'en', endonym: 'English', englishName: 'English' },
  { code: 'hi', endonym: 'हिन्दी', englishName: 'Hindi' },
  { code: 'mr', endonym: 'मराठी', englishName: 'Marathi' },
  { code: 'bn', endonym: 'বাংলা', englishName: 'Bengali' },
  { code: 'ta', endonym: 'தமிழ்', englishName: 'Tamil' },
  { code: 'te', endonym: 'తెలుగు', englishName: 'Telugu' },
];

const SUPPORTED_CODES = SUPPORTED_LANGUAGES.map((l) => l.code);

export const resources = {
  en: { translation: en },
  hi: { translation: hi },
  mr: { translation: mr },
  bn: { translation: bn },
  ta: { translation: ta },
  te: { translation: te },
} as const;

export function isSupportedLanguage(code: string | null | undefined): code is LanguageCode {
  return !!code && (SUPPORTED_CODES as string[]).includes(code);
}

/** The device language, if we support it. */
export function deviceLanguage(): LanguageCode {
  const locales = Localization.getLocales();
  for (const locale of locales) {
    if (isSupportedLanguage(locale.languageCode)) return locale.languageCode;
  }
  return 'en';
}

export async function loadStoredLanguage(): Promise<LanguageCode | null> {
  try {
    const stored = await AsyncStorage.getItem(STORAGE_KEY_LANGUAGE);
    return isSupportedLanguage(stored) ? stored : null;
  } catch {
    return null;
  }
}

export async function persistLanguage(code: LanguageCode): Promise<void> {
  try {
    await AsyncStorage.setItem(STORAGE_KEY_LANGUAGE, code);
  } catch {
    // Non-fatal: the language still applies for this session.
  }
}

let initialised = false;

export async function initI18n(): Promise<LanguageCode> {
  const stored = await loadStoredLanguage();
  const language = stored ?? deviceLanguage();

  if (!initialised) {
    await i18n.use(initReactI18next).init({
      resources,
      lng: language,
      fallbackLng: 'en',
      // Locale files are flat-ish and hand-authored; `.` is our only separator.
      keySeparator: '.',
      nsSeparator: false,
      interpolation: { escapeValue: false },
      returnNull: false,
      compatibilityJSON: 'v4',
    });
    initialised = true;
  } else {
    await i18n.changeLanguage(language);
  }

  return language;
}

export async function changeLanguage(code: LanguageCode): Promise<void> {
  await i18n.changeLanguage(code);
  await persistLanguage(code);
}

export default i18n;
