import { describe, expect, it } from 'vitest';
import { COLOR_TOKEN_KEYS, darkColors, lightColors, resolveThemeMode, THEME_PREFERENCE_KEY } from './palettes';

describe('theme preference', () => {
  it('uses one canonical storage key', () => {
    expect(THEME_PREFERENCE_KEY).toBe('themePreference');
  });

  it('lets an explicit choice win over system appearance', () => {
    expect(resolveThemeMode('dark', 'light')).toBe('dark');
    expect(resolveThemeMode('light', 'dark')).toBe('light');
  });

  it('falls back to system appearance when nothing is saved', () => {
    expect(resolveThemeMode(null, 'dark')).toBe('dark');
    expect(resolveThemeMode(undefined, 'light')).toBe('light');
    expect(resolveThemeMode('system', 'dark')).toBe('dark');
  });
});

describe('theme tokens', () => {
  it('covers the same token names in light and dark', () => {
    expect(Object.keys(darkColors).sort()).toEqual(Object.keys(lightColors).sort());
    for (const key of COLOR_TOKEN_KEYS) {
      expect(lightColors[key]).toBeTruthy();
      expect(darkColors[key]).toBeTruthy();
    }
  });

  it('keeps dark body text lighter than the dark background', () => {
    expect(darkColors.text).not.toBe(darkColors.background);
    expect(darkColors.textPrimary).toBe(darkColors.text);
    expect(lightColors.text).not.toBe(lightColors.background);
    expect(lightColors.surfaceSecondary).toBe(lightColors.surfaceAlt);
    expect(darkColors.inputBackground).toBe(darkColors.glassInput);
  });
});

function hexChannel(hex: string, index: number): number {
  const value = hex.replace('#', '');
  return parseInt(value.slice(index * 2, index * 2 + 2), 16) / 255;
}

function relativeLuminance(hex: string): number {
  const linear = (channel: number) =>
    channel <= 0.03928 ? channel / 12.92 : ((channel + 0.055) / 1.055) ** 2.4;
  return (
    0.2126 * linear(hexChannel(hex, 0)) +
    0.7152 * linear(hexChannel(hex, 1)) +
    0.0722 * linear(hexChannel(hex, 2))
  );
}

function contrastRatio(a: string, b: string): number {
  const first = relativeLuminance(a);
  const second = relativeLuminance(b);
  const [hi, lo] = first > second ? [first, second] : [second, first];
  return (hi + 0.05) / (lo + 0.05);
}

describe('selected control tokens', () => {
  it('keeps light selected chips navy-on-white and light segments white-on-navy', () => {
    expect(lightColors.controlSelectedBackground).toBe('#102A43');
    expect(lightColors.controlSelectedText).toBe('#FFFFFF');
    expect(lightColors.controlSelectedIcon).toBe('#FFFFFF');
    expect(lightColors.segmentSelectedBackground).toBe('#FFFFFF');
    expect(lightColors.segmentSelectedText).toBe('#102A43');
    expect(lightColors.navSelectedBackground).toBe('#EAF6FF');
    expect(lightColors.navSelectedForeground).toBe('#0757D9');
  });

  it('does not reuse the ice inverse surface as a dark selected background', () => {
    expect(darkColors.controlSelectedBackground).not.toBe(darkColors.inverse);
    expect(darkColors.segmentSelectedBackground).not.toBe(darkColors.inverse);
    expect(darkColors.navSelectedBackground).not.toBe(darkColors.inverse);
    expect(darkColors.controlSelectedBackground).not.toBe(darkColors.surface);
    expect(darkColors.segmentSelectedBackground).not.toBe(darkColors.surface);
  });

  it('keeps dark selected backgrounds blue-tinted and darker than selected text', () => {
    expect(relativeLuminance(darkColors.controlSelectedBackground)).toBeLessThan(0.35);
    expect(relativeLuminance(darkColors.segmentSelectedBackground)).toBeLessThan(0.35);
    expect(relativeLuminance(darkColors.navSelectedBackground)).toBeLessThan(0.35);
    expect(relativeLuminance(darkColors.controlSelectedText)).toBeGreaterThan(0.8);
    expect(relativeLuminance(darkColors.controlSelectedIcon)).toBeGreaterThan(0.8);
    expect(relativeLuminance(darkColors.segmentSelectedText)).toBeGreaterThan(0.8);
    expect(relativeLuminance(darkColors.navSelectedForeground)).toBeGreaterThan(0.8);
  });

  it('gives dark selected chips, segments, and nav readable contrast', () => {
    expect(
      contrastRatio(darkColors.controlSelectedBackground, darkColors.controlSelectedText),
    ).toBeGreaterThan(4.5);
    expect(
      contrastRatio(darkColors.controlSelectedBackground, darkColors.controlSelectedIcon),
    ).toBeGreaterThan(4.5);
    expect(
      contrastRatio(darkColors.segmentSelectedBackground, darkColors.segmentSelectedText),
    ).toBeGreaterThan(4.5);
    expect(
      contrastRatio(darkColors.navSelectedBackground, darkColors.navSelectedForeground),
    ).toBeGreaterThan(4.5);
    expect(
      contrastRatio(lightColors.controlSelectedBackground, lightColors.controlSelectedText),
    ).toBeGreaterThan(4.5);
    expect(
      contrastRatio(lightColors.segmentSelectedBackground, lightColors.segmentSelectedText),
    ).toBeGreaterThan(4.5);
  });

  it('keeps selected distinct from unselected, disabled, and hover surfaces', () => {
    expect(darkColors.controlSelectedBackground).not.toBe(darkColors.surfaceAlt);
    expect(darkColors.controlSelectedBackground).not.toBe(darkColors.disabled);
    expect(darkColors.controlSelectedBackground).not.toBe(darkColors.primarySurface);
    expect(darkColors.segmentSelectedBackground).not.toBe(darkColors.glass);
    expect(darkColors.disabled).not.toBe(darkColors.controlSelectedBackground);
  });
});
