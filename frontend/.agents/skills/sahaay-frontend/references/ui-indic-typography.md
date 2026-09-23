# ui-indic-typography

**Always use `Text` from `@/components/ui`. Never import `Text` from `react-native`.**

## Why it matters

Devanagari, Bengali, Tamil and Telugu need more vertical room than Latin at the same nominal
font size. Devanagari has the shirorekha above and matras below; Tamil and Telugu have tall
loops and descenders. React Native's default line height is tuned for Latin, so these scripts
get visibly clipped — and the developer testing in English never sees it.

Our `Text` also caps font scaling at 1.6×, so a user with large system text gets bigger type
without shattering the layout.

## Wrong

```tsx
import { Text } from 'react-native';

<Text style={{ fontSize: 16 }}>सूक्ष्म ऋण वित्त योजना</Text>;
// renders with ~19px leading — the matras below the baseline are cut off
```

## Right

```tsx
import { Text } from '@/components/ui';

<Text variant="body">{pickLocalized(scheme.name, language)}</Text>;
// body = 16px / 26px line height — enough room for every script we ship
```

## The scale

```
display    30/40      title       24/34      heading    20/30
subheading 17/26      body        16/26      bodyStrong 16/26
caption    14/22      label       13/18
```

The second number is line height. The ratios look generous in a Latin screenshot. **They are
not padding — do not tighten them.**

## Checking a language

After adding or changing a locale, look at these four places in a non-Latin script:

1. **Tab bar labels** — shortest space, breaks first
2. **Button labels** — wrap or truncate?
3. **Chips** — fixed-height, so clipping shows immediately
4. **Stat rows on `SchemeCard`** — three columns of numbers plus labels

```bash
# switch language from the Profile tab, or set it as the device language
```

## Notes

- `allowFontScaling={false}` is acceptable only for decorative glyphs (the emoji tab icons),
  never for text carrying meaning.
- Emoji are used as icons in v0. Every one is paired with a text label, so nothing depends on
  the glyph rendering — see `DESIGN_SYSTEM.md`.
- No custom font is bundled. System fonts have the widest Indic script coverage on cheap
  Android devices; a webfont that lacks a glyph renders tofu.
