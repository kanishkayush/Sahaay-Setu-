/**
 * Light and dark color palettes.
 *
 * Token names stay identical across modes so screens consume one theme object.
 * Dark is a professional navy equivalent of the ice/blue UI — not a naive invert.
 */

export type ThemeMode = 'light' | 'dark';

export type ColorTokens = {
  background: string;
  surface: string;
  surfaceAlt: string;
  surfaceSecondary: string;
  inverse: string;
  inverseAlt: string;

  glass: string;
  glassBorder: string;
  glassStrong: string;
  glassInput: string;
  inputBackground: string;

  text: string;
  textPrimary: string;
  textSecondary: string;
  textMuted: string;
  textInverse: string;
  textOnInverse: string;

  border: string;
  borderSoft: string;
  borderStrong: string;
  borderGlass: string;

  primary: string;
  primaryDark: string;
  primaryLight: string;
  primarySurface: string;
  primaryText: string;
  blue: string;

  accent: string;
  accentSurface: string;

  success: string;
  warning: string;
  danger: string;
  error: string;
  info: string;

  successText: string;
  warningText: string;
  dangerText: string;
  infoText: string;

  successSurface: string;
  warningSurface: string;
  dangerSurface: string;
  infoSurface: string;

  overlay: string;
  disabled: string;

  /** Solid selected chips, filters, language pills. */
  controlSelectedBackground: string;
  controlSelectedText: string;
  controlSelectedBorder: string;
  controlSelectedIcon: string;

  /** Selected segment inside a track (Nearby/List, theme toggle). */
  segmentSelectedBackground: string;
  segmentSelectedText: string;

  /** Active bottom-nav item. Light stays ice+blue; dark stays a blue pill. */
  navSelectedBackground: string;
  navSelectedForeground: string;

  gradient: readonly [string, string, string];
};

export const lightColors: ColorTokens = {
  background: '#F4FAFF',
  surface: '#FFFFFF',
  surfaceAlt: '#F0F4F8',
  surfaceSecondary: '#F0F4F8',
  inverse: '#102A43',
  inverseAlt: '#063B9E',

  glass: 'rgba(255, 255, 255, 0.62)',
  glassBorder: 'rgba(255, 255, 255, 0.70)',
  glassStrong: 'rgba(255, 255, 255, 0.78)',
  glassInput: 'rgba(255, 255, 255, 0.82)',
  inputBackground: 'rgba(255, 255, 255, 0.82)',

  text: '#102A43',
  textPrimary: '#102A43',
  textSecondary: '#52657A',
  textMuted: '#5E7184',
  textInverse: '#FFFFFF',
  textOnInverse: '#B3CDE0',

  border: 'rgba(7, 87, 217, 0.15)',
  borderSoft: 'rgba(7, 87, 217, 0.08)',
  borderStrong: 'rgba(7, 87, 217, 0.3)',
  borderGlass: 'rgba(255, 255, 255, 0.70)',

  primary: '#0757D9',
  primaryDark: '#063B9E',
  primaryLight: '#1677E8',
  primarySurface: '#EAF6FF',
  primaryText: '#FFFFFF',
  blue: '#0757D9',

  accent: '#E58A2B',
  accentSurface: '#FFF7E6',

  success: '#159447',
  warning: '#E58A2B',
  danger: '#D92D4F',
  error: '#D92D4F',
  info: '#0757D9',

  successText: '#159447',
  warningText: '#B45309',
  dangerText: '#D92D4F',
  infoText: '#0757D9',

  successSurface: '#EAF7EF',
  warningSurface: '#FFF7E6',
  dangerSurface: '#FEF2F2',
  infoSurface: '#EAF6FF',

  overlay: 'rgba(0, 0, 0, 0.45)',
  disabled: '#93A1B0',

  controlSelectedBackground: '#102A43',
  controlSelectedText: '#FFFFFF',
  controlSelectedBorder: '#102A43',
  controlSelectedIcon: '#FFFFFF',

  segmentSelectedBackground: '#FFFFFF',
  segmentSelectedText: '#102A43',

  navSelectedBackground: '#EAF6FF',
  navSelectedForeground: '#0757D9',

  gradient: ['#F4FAFF', '#EAF6FF', '#F8FCFF'],
};

export const darkColors: ColorTokens = {
  background: '#0B1220',
  surface: '#152033',
  surfaceAlt: '#1C2A40',
  surfaceSecondary: '#1C2A40',
  inverse: '#EAF6FF',
  inverseAlt: '#7AA8E0',

  glass: 'rgba(21, 32, 51, 0.82)',
  glassBorder: 'rgba(154, 186, 224, 0.22)',
  glassStrong: 'rgba(21, 32, 51, 0.94)',
  glassInput: 'rgba(28, 42, 64, 0.96)',
  inputBackground: 'rgba(28, 42, 64, 0.96)',

  text: '#F4F7FB',
  textPrimary: '#F4F7FB',
  textSecondary: '#C5D2E0',
  textMuted: '#A7B7C9',
  textInverse: '#102A43',
  textOnInverse: '#1C3A5A',

  border: 'rgba(126, 168, 224, 0.32)',
  borderSoft: 'rgba(126, 168, 224, 0.18)',
  borderStrong: 'rgba(126, 168, 224, 0.52)',
  borderGlass: 'rgba(154, 186, 224, 0.22)',

  primary: '#4C8DFF',
  primaryDark: '#2F6FE0',
  primaryLight: '#7AAFFF',
  primarySurface: '#163056',
  primaryText: '#F4F7FB',
  blue: '#4C8DFF',

  accent: '#F0A04A',
  accentSurface: '#3A2A16',

  success: '#3DCF7A',
  warning: '#F0A04A',
  danger: '#F07186',
  error: '#F07186',
  info: '#4C8DFF',

  successText: '#5EDC94',
  warningText: '#F5C07A',
  dangerText: '#FF8A9B',
  infoText: '#7AAFFF',

  successSurface: '#123526',
  warningSurface: '#3A2A16',
  dangerSurface: '#3A1A22',
  infoSurface: '#163056',

  overlay: 'rgba(0, 0, 0, 0.65)',
  disabled: '#6E7F93',

  controlSelectedBackground: '#2F6FE0',
  controlSelectedText: '#FFFFFF',
  controlSelectedBorder: '#7AAFFF',
  controlSelectedIcon: '#FFFFFF',

  segmentSelectedBackground: '#2F6FE0',
  segmentSelectedText: '#FFFFFF',

  navSelectedBackground: '#2F6FE0',
  navSelectedForeground: '#FFFFFF',

  gradient: ['#0B1220', '#122038', '#0E1728'],
};

export const palettes: Record<ThemeMode, ColorTokens> = {
  light: lightColors,
  dark: darkColors,
};

export const COLOR_TOKEN_KEYS = Object.keys(lightColors) as (keyof ColorTokens)[];

/** Single canonical persistence key. Values: `light` | `dark`. */
export const THEME_PREFERENCE_KEY = 'themePreference';

export function resolveThemeMode(
  preference: string | null | undefined,
  system: string | null | undefined,
): ThemeMode {
  if (preference === 'light' || preference === 'dark') return preference;
  return system === 'dark' ? 'dark' : 'light';
}
