# lang-placeholders

**`{{count}}`, `{{rate}}`, `{{months}}` are code. Translate around them, never through them.
Plurals use i18next suffixes, not concatenation.**

## Why it matters

A translated placeholder never substitutes — it renders as literal text, so the user sees
`{{गिनती}} योजनाएँ` instead of a number. And English plural rules do not transfer: Indic
languages have different plural categories, so building a sentence by concatenating a number
and a noun produces wrong grammar in most of the languages we ship.

## Wrong

```jsonc
{ "resultsSubtitle": "{{गिनती}} योजनाएँ मिलीं" }      // ← placeholder translated
{ "resultsSubtitle": "{{ count }} schemes" }          // ← spaces inside the braces
{ "found": "मिला" }                                   // then: `${count} ${t('found')}`
```

```tsx
<Text>
  {count} {t('recommender.schemes')}
</Text> // ← word order is not universal
```

## Right

```jsonc
{
  "recommender": {
    "resultsSubtitle": "{{count}} scheme matched your details",
    "resultsSubtitle_other": "{{count}} schemes matched your details",
  },
  "schemes": {
    "moratoriumRange": "{{min}}–{{max}} months",
    "womenRate": "Women pay just {{rate}}%",
  },
}
```

```tsx
t('recommender.resultsSubtitle', { count });
t('schemes.moratoriumRange', { min: scheme.moratoriumMinMonths, max: scheme.moratoriumMaxMonths });
```

The whole sentence is one key, so a translator can reorder it freely.

## Plurals

i18next picks the suffix from the language's own plural rules:

```jsonc
{
  "resultsSubtitle": "{{count}} योजना आपके विवरण से मेल खाती है",
  "resultsSubtitle_other": "{{count}} योजनाएँ आपके विवरण से मेल खाती हैं",
}
```

Pass `count` and i18next selects. Never branch in the component.

## Formatted values

Format before interpolating, so the placeholder receives a display-ready string:

```tsx
t('recommender.atRate', { rate: formatPercent(recommendation.applicableInterestRatePct) });
t('partners.distance', { distance: formatDistance(partner.distanceKm) });
```

This keeps Indian number grouping (₹1,40,000) and percentage formatting consistent, and out of
the locale files.

## Notes

- `escapeValue: false` is set — React already escapes, so double-escaping would mangle Indic
  text.
- Interpolating something itself user-visible (a scheme name) means localising it first:
  `t('calculator.presetFromScheme', { scheme: pickLocalized(scheme.name, language) })`.
- The translation issue template asks contributors to confirm placeholders are intact.
