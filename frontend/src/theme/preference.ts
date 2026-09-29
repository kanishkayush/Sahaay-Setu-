import AsyncStorage from '@react-native-async-storage/async-storage';
import { Appearance } from 'react-native';

import { palettes, resolveThemeMode, THEME_PREFERENCE_KEY, type ColorTokens, type ThemeMode } from './palettes';

export type ThemePreference = ThemeMode;
export { THEME_PREFERENCE_KEY, resolveThemeMode };

let appliedMode: ThemeMode = 'light';

export function paletteFor(mode: ThemeMode): ColorTokens {
  return palettes[mode];
}

export function getAppliedThemeMode(): ThemeMode {
  return appliedMode;
}

export function setAppliedThemeMode(mode: ThemeMode): void {
  appliedMode = mode;
}

export async function readStoredThemePreference(): Promise<ThemePreference | null> {
  try {
    const saved = await AsyncStorage.getItem(THEME_PREFERENCE_KEY);
    if (saved === 'light' || saved === 'dark') return saved;
    return null;
  } catch {
    return null;
  }
}

export async function writeStoredThemePreference(preference: ThemePreference): Promise<void> {
  await AsyncStorage.setItem(THEME_PREFERENCE_KEY, preference);
}

export async function hydrateThemePreference(): Promise<{
  preference: ThemePreference | null;
  mode: ThemeMode;
}> {
  const preference = await readStoredThemePreference();
  const mode = resolveThemeMode(preference, Appearance.getColorScheme());
  setAppliedThemeMode(mode);
  return { preference, mode };
}
