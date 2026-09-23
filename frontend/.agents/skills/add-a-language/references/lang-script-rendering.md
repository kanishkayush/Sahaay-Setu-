# lang-script-rendering

**Check the script on a device, not just the strings in a file. Indic text is taller and longer
than the English it replaces.**

## Why it matters

Two failure modes a developer testing in English never sees:

**Vertical clipping.** Devanagari has the shirorekha above and matras below the baseline; Tamil
and Telugu have tall loops and descenders. React Native's Latin-tuned default line height cuts
them off.

**Horizontal overflow.** Translations commonly run 20–40% longer. Tab bar labels break first,
then buttons, then chips.

Both look fine in a JSON diff.

## Wrong

```tsx
import { Text } from 'react-native';
<Text style={{ fontSize: 16 }}>सूक्ष्म ऋण वित्त योजना</Text>;
// ~19px leading — the matras below the baseline are cut
```

```tsx
<View style={{ height: 32 }}>
  <Text variant="label">{t('partners.status.NOT_ACCEPTING')}</Text>
</View>
// fixed height clips a taller script
```

```tsx
<Text numberOfLines={1}>{t('nav.calculator')}</Text>
// silently truncates mid-word in a longer language
```

## Right

```tsx
import { Text } from '@/components/ui';
<Text variant="body">{pickLocalized(scheme.name, language)}</Text>;
```

```tsx
<View style={{ minHeight: 32, paddingVertical: spacing.sm }}>   // minHeight, not height
```

Our `Text` carries the roomier line heights and caps font scaling at 1.6×.

## The four-place check

After adding or extending a language, switch to it from the Profile tab and look at:

1. **Tab bar labels** — least space, breaks first
2. **Button labels** — wrap or truncate?
3. **Chips** — fixed-ish height, so clipping shows immediately
4. **`SchemeCard` stat row** — three columns of numbers _and_ labels, the tightest layout

Then bump the device font size to maximum and check 1 and 2 again.

## The scale

```
display 30/40 · title 24/34 · heading 20/30 · subheading 17/26
body 16/26 · bodyStrong 16/26 · caption 14/22 · label 13/18
```

The second number is line height. It looks generous in a Latin screenshot. **It is not padding
— do not tighten it.**

## Notes

- Emoji are used as icons in v0, always paired with a text label, so nothing depends on glyph
  rendering.
- No custom font is bundled — system fonts have the widest Indic coverage on cheap Android, and
  a webfont missing a glyph renders tofu.
- `allowFontScaling={false}` is acceptable only on decorative glyphs, never on meaningful text.
- If a string genuinely cannot fit, shorten the source English rather than truncating the
  translation.
