# i18n-strings

**No user-visible string is ever written inline. Add the key to `src/i18n/locales/en.json`
and render it with `t()`.**

## Why it matters

This app exists to reach people in their own language. A hardcoded English string is invisible
to `npm run i18n:check`, so it will never be translated and nobody will notice it is missing.
"Temporary" and "debug" strings ship.

## Wrong

```tsx
<Text variant="title">Find my scheme</Text>
<Button title="Next" onPress={next} />
<Text>{`${count} schemes matched`}</Text>          // ← also breaks pluralisation
```

## Right

```tsx
const { t } = useTranslation();

<Text variant="title">{t('recommender.title')}</Text>
<Button title={t('common.next')} onPress={next} />
<Text>{t('recommender.resultsSubtitle', { count })}</Text>
```

```jsonc
// src/i18n/locales/en.json
{
  "recommender": {
    "resultsSubtitle": "{{count}} scheme matched your details",
    "resultsSubtitle_other": "{{count}} schemes matched your details",
  },
}
```

## Rules

- **`en.json` is the baseline.** A key that does not exist there does not exist. Other locales
  may be partial — English is the fallback for every key.
- **Placeholders are code.** `{{count}}`, `{{rate}}`, `{{months}}` must survive translation
  intact. Translate around them, never through them.
- **Plurals use i18next suffixes** (`_one`, `_other`), not string concatenation. Indic
  languages have plural rules that differ from English.
- **Enum values get their own namespace** so they can be looked up dynamically:
  `t(\`category.${scheme.category}\`)`, `t(\`partners.type.${partner.type}\`)`.

## Checking

```bash
npm run i18n:check
```

Reports coverage per locale. **Fails** only on keys present in a locale but missing from
`en.json` — almost always a typo or a leftover from a rename. Missing translations are a
warning, by design (ADR-006).

## Notes

- Backend content — scheme names, eligibility labels — is a different thing entirely and does
  **not** use `t()`. See `i18n-localized-content.md`.
- Interpolated values that are themselves user-visible (a scheme name) must be localised
  before interpolation, not after.
