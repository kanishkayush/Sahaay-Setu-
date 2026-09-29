import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import { Appearance } from 'react-native';

import { lightColors, palettes, type ColorTokens, type ThemeMode } from './palettes';
import {
  hydrateThemePreference,
  setAppliedThemeMode,
  writeStoredThemePreference,
  type ThemePreference,
} from './preference';

type ThemeContextValue = {
  colors: ColorTokens;
  mode: ThemeMode;
  preference: ThemePreference | null;
  setPreference: (preference: ThemePreference) => Promise<void>;
  ready: boolean;
};

const ThemeContext = createContext<ThemeContextValue | null>(null);

const fallback: ThemeContextValue = {
  colors: lightColors,
  mode: 'light',
  preference: null,
  setPreference: async () => {},
  ready: true,
};

export function ThemeProvider({
  children,
  initialMode = 'light',
  initialPreference = null,
}: {
  children: ReactNode;
  initialMode?: ThemeMode;
  initialPreference?: ThemePreference | null;
}) {
  const [mode, setMode] = useState<ThemeMode>(initialMode);
  const [preference, setPreferenceState] = useState<ThemePreference | null>(initialPreference);
  const [ready, setReady] = useState(Boolean(initialPreference) || initialMode !== undefined);

  useEffect(() => {
    let cancelled = false;
    hydrateThemePreference()
      .then(({ preference: saved, mode: resolved }) => {
        if (cancelled) return;
        setPreferenceState(saved);
        setMode(resolved);
        setAppliedThemeMode(resolved);
      })
      .finally(() => {
        if (!cancelled) setReady(true);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (preference) return;
    const sub = Appearance.addChangeListener(({ colorScheme }) => {
      const next: ThemeMode = colorScheme === 'dark' ? 'dark' : 'light';
      setMode(next);
      setAppliedThemeMode(next);
    });
    return () => sub.remove();
  }, [preference]);

  const setPreference = useCallback(async (next: ThemePreference) => {
    setPreferenceState(next);
    setMode(next);
    setAppliedThemeMode(next);
    await writeStoredThemePreference(next);
  }, []);

  const value = useMemo<ThemeContextValue>(
    () => ({
      colors: palettes[mode],
      mode,
      preference,
      setPreference,
      ready,
    }),
    [mode, preference, setPreference, ready],
  );

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme(): ThemeContextValue {
  return useContext(ThemeContext) ?? fallback;
}
