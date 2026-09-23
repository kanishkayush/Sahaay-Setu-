# i18n-localized-content

**Backend content arrives as a `LocalizedText` map and is read with `pickLocalized()`. It never
goes through `t()`.**

## Why it matters

There are two distinct kinds of translatable text, and conflating them breaks both:

|           | UI copy                         | Backend content                                    |
| --------- | ------------------------------- | -------------------------------------------------- |
| Examples  | button labels, errors, headings | scheme names, eligibility labels, document lists   |
| Source    | `src/i18n/locales/*.json`       | the API response                                   |
| Read with | `t('schemes.title')`            | `pickLocalized(scheme.name, language)`             |
| Why       | it is part of the app           | it is **data** — it changes without an app release |

Scheme names cannot be i18n keys because the catalogue is data owned by the backend. Adding a
scheme must not require shipping a new app build.

## Wrong

```tsx
<Text>{t(`scheme.${scheme.id}.name`)}</Text>     // ← key won't exist; renders raw
<Text>{scheme.name}</Text>                        // ← renders "[object Object]"
<Text>{scheme.name.en}</Text>                     // ← always English, ignores the user
<Text>{scheme.name[language]}</Text>              // ← undefined for a partial locale
```

That last one is the subtle one: `LocalizedText` is a partial map. A scheme translated into
`en` and `hi` renders blank for a Tamil user.

## Right

```tsx
import { pickLocalized } from '@/i18n/localized';

const name = pickLocalized(scheme.name, language, scheme.code);
<Text variant="subheading">{name}</Text>;
```

`pickLocalized` tries the requested language, falls back to `en`, then to the third argument.

## The shape

```jsonc
{
  "name": {
    "en": "Micro Credit Finance Scheme", // ← mandatory, enforced by the Zod schema
    "hi": "सूक्ष्म ऋण वित्त योजना",
    "ta": "நுண் கடன் திட்டம்",
  },
}
```

`LocalizedTextSchema` requires `en`. That is what makes the fallback safe everywhere.

## Notes

- Applies to `Scheme.name`, `Scheme.shortDescription`, `EligibilityRule.label`,
  `Scheme.documentsRequired[]`, `MatchReason.text`, and `dataDisclaimer`.
- `ChannelPartner` is different again: `name` is a plain string (the legal name), with
  `localizedNames` as an optional transliteration map. Read it as
  `partner.localizedNames?.[language] ?? partner.name` — a bank's registered name is not
  always something to translate.
- Always pass a sensible third argument. `scheme.code` beats an empty string on screen.
