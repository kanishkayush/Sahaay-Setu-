/**
 * Design tokens — Sahaay Setu Premium Glassmorphism.
 *
 * Government financial services + modern fintech + subtle glass.
 * Every glass surface must maintain text readability (≥4.5:1 contrast).
 */

export const colors = {
  // ── Surface ────────────────────────────────────────────────────────────
  background: '#F4FAFF',     // Pale Ice
  surface: '#FFFFFF',
  surfaceAlt: '#F0F4F8',
  inverse: '#102A43',        // Dark Navy
  inverseAlt: '#063B9E',

  // ── Glass ──────────────────────────────────────────────────────────────
  glass: 'rgba(255, 255, 255, 0.62)',
  glassBorder: 'rgba(255, 255, 255, 0.70)',
  glassStrong: 'rgba(255, 255, 255, 0.78)',
  glassInput: 'rgba(255, 255, 255, 0.82)',

  // ── Foreground ramp ────────────────────────────────────────────────────
  text: '#102A43',           // Dark Navy
  textSecondary: '#52657A',  // Secondary Text
  textMuted: '#7D8C9C',
  textInverse: '#FFFFFF',
  textOnInverse: '#B3CDE0',

  // ── Border ─────────────────────────────────────────────────────────────
  border: 'rgba(7, 87, 217, 0.15)', // Light blue border tint
  borderSoft: 'rgba(7, 87, 217, 0.08)',
  borderStrong: 'rgba(7, 87, 217, 0.3)',
  borderGlass: 'rgba(255, 255, 255, 0.70)',

  // ── Accent ─────────────────────────────────────────────────────────────
  primary: '#0757D9',         // Royal Blue
  primaryDark: '#063B9E',     // Deep Royal Blue
  primaryLight: '#1677E8',    // Mid Blue
  primarySurface: '#EAF6FF',  // Ice Blue
  blue: '#0757D9',            // Vivid blue for links/icons

  accent: '#E58A2B',          // Restrained saffron
  accentSurface: '#FFF7E6',

  // ── Semantic: vivid for fills and icons ────────────────────────────────
  success: '#159447',
  warning: '#E58A2B',
  danger: '#D92D4F',          // Destructive Coral
  info: '#0757D9',

  // ── Semantic: darkened for TEXT (all ≥ 4.5:1 on white) ─────────────────
  successText: '#159447',
  warningText: '#B45309',
  dangerText: '#D92D4F',
  infoText: '#0757D9',

  successSurface: '#EAF7EF',
  warningSurface: '#FFF7E6',
  dangerSurface: '#FEF2F2',
  infoSurface: '#EAF6FF',

  overlay: 'rgba(0, 0, 0, 0.45)',
} as const;

/** --space-* from the source, plus the xxxl step our screens already use. */
export const spacing = {
  xs: 4,
  sm: 8,
  md: 12,
  lg: 16,
  xl: 20,
  xxl: 24,
  xxxl: 32,
  section: 40,
} as const;

/** --radius-* — increased for premium rounded feel. */
export const radius = {
  sm: 8,
  md: 14,
  lg: 20,
  xl: 28,
  pill: 980,
} as const;

/**
 * Type scale.
 *
 * Sizes follow the source's --text-* ramp; line heights are ours, sized for
 * Indic scripts. `label` is 13px — the source's 12px xs floor is raised here,
 * and the literal 10/11px in the mockups is not used at all.
 */
export const typography = {
  hero: { fontSize: 40, lineHeight: 46, fontWeight: '700', letterSpacing: -0.6 },
  display: { fontSize: 28, lineHeight: 36, fontWeight: '700', letterSpacing: -0.4 },
  title: { fontSize: 24, lineHeight: 32, fontWeight: '700', letterSpacing: -0.3 },
  heading: { fontSize: 21, lineHeight: 29, fontWeight: '600', letterSpacing: -0.2 },
  subheading: { fontSize: 18, lineHeight: 26, fontWeight: '600' },
  body: { fontSize: 17, lineHeight: 26, fontWeight: '400' },
  bodyStrong: { fontSize: 17, lineHeight: 26, fontWeight: '600' },
  caption: { fontSize: 15, lineHeight: 23, fontWeight: '400' },
  label: { fontSize: 13, lineHeight: 18, fontWeight: '600', letterSpacing: 0.3 },
  /** Figures — tabular so columns of money line up. */
  mono: { fontSize: 17, lineHeight: 24, fontWeight: '600' },
  statValue: { fontSize: 26, lineHeight: 32, fontWeight: '700', letterSpacing: -0.4 },
} as const;

/** --elev-* — refined for glassmorphism. */
export const shadow = {
  flat: {},
  card: {
    shadowColor: '#0757D9',
    shadowOpacity: 0.06,
    shadowRadius: 20,
    shadowOffset: { width: 0, height: 6 },
    elevation: 3,
  },
  raised: {
    shadowColor: '#0757D9',
    shadowOpacity: 0.1,
    shadowRadius: 32,
    shadowOffset: { width: 0, height: 12 },
    elevation: 6,
  },
  glass: {
    shadowColor: '#0757D9',
    shadowOpacity: 0.08,
    shadowRadius: 30,
    shadowOffset: { width: 0, height: 8 },
    elevation: 4,
  },
} as const;

/** --motion-* from the source. */
export const motion = { fast: 150, base: 220 } as const;

/**
 * Minimum tappable size. The source's iOS sheet uses 44px (Apple's HIG floor);
 * we hold to 48 across both platforms, matching its own Android sheet (52–56px)
 * and our users' devices.
 */
export const MIN_TOUCH_SIZE = 48;

export const theme = { colors, spacing, radius, typography, shadow, motion } as const;
export type Theme = typeof theme;
