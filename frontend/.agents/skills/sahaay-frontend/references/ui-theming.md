# ui-theming

**Every colour, spacing, radius and type value comes from `@/theme`. No literals in
components.**

## Why it matters

These tokens encode decisions that are easy to break by accident: contrast ratios verified
against WCAG AA for outdoor readability, spacing that keeps touch targets apart, and line
heights sized for Indic scripts. A hand-picked `#666` or `padding: 10` quietly opts that
element out of all of it.

## Wrong

```tsx
const styles = StyleSheet.create({
  card: {
    backgroundColor: '#fff',
    padding: 15,
    borderRadius: 8,
    borderColor: '#ddd', // ← 1.4:1 against white — invisible in sunlight
  },
  label: { fontSize: 12, color: '#999' }, // ← below the 13px floor, fails contrast
});
```

## Right

```tsx
import { colors, radius, spacing } from '@/theme';

const styles = StyleSheet.create({
  card: {
    backgroundColor: colors.surface,
    padding: spacing.lg,
    borderRadius: radius.lg,
    borderColor: colors.border,
  },
});
```

```tsx
// type comes from the Text component's variant, not a fontSize
<Text variant="label" color={colors.textMuted}>
  {t('schemes.loanRange')}
</Text>
```

## The tokens

```
spacing   xs 4 · sm 8 · md 12 · lg 16 · xl 24 · xxl 32 · xxxl 48
radius    sm 6 · md 10 · lg 16 · xl 24 · pill 999
colors    primary · accent · success · warning · danger · info
          (each with a matching low-saturation *Surface*)
          background · surface · surfaceAlt · border · borderStrong
          text · textSecondary · textMuted · textInverse
MIN_TOUCH_SIZE  48
```

Status colours always ship in pairs — `danger` for the text or icon, `dangerSurface` for the
background behind it.

## Notes

- **One accent per screen.** `colors.accent` marks the single most important action. Two accent
  elements means neither reads as primary.
- Need a value the theme lacks? Add it to `src/theme/index.ts` with a comment explaining the
  constraint it encodes — do not inline it.
- The palette is defined light-first and there is no dark mode yet. Do not add
  `useColorScheme()` branches to individual components; that belongs in the theme when it lands.
- Shadows come from `shadow.card` / `shadow.raised` so elevation stays consistent across
  Android and iOS.
