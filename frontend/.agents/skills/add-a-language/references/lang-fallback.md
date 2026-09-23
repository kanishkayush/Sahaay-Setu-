# lang-fallback

**English is the fallback for every key. A partial locale is a valid, shippable locale.**

## Why it matters

Six languages cannot all be translated well in a hackathon timeline. The choice was: ship two
complete languages, or six with English filling the gaps. The second reaches far more people,
and a user seeing occasional English is fine — a user seeing `recommender.resultsTitle` is
looking at a broken app.

This is what lets translations land one PR at a time without ever gating a release (ADR-006).

## How it works

```ts
await i18n.use(initReactI18next).init({
  resources,
  lng: language,
  fallbackLng: 'en', // ← every missing key resolves here
  keySeparator: '.',
  nsSeparator: false,
  returnNull: false,
});
```

Backend content has its own fallback, because it is data rather than UI copy:

```ts
export function pickLocalized(text, language, fallback = '') {
  if (!text) return fallback;
  return text[language] ?? text.en ?? fallback;
}
```

`LocalizedTextSchema` _requires_ `en`, which is what makes that chain safe.

## Wrong

```ts
fallbackLng: false,          // ← missing keys render as raw key strings
returnNull: true,            // ← missing keys render as "null"
```

```tsx
<Text>{scheme.name[language]}</Text> // ← blank for any partially translated scheme
```

```ts
// blocking a language until it is complete
if (coverage < 100) throw new Error('incomplete locale');
```

## Right

```tsx
<Text>{t('recommender.resultsTitle')}</Text>              // English if untranslated
<Text>{pickLocalized(scheme.name, language, scheme.code)}</Text>
```

Always pass a third argument to `pickLocalized` — `scheme.code` reads better than an empty
string if both the locale and `en` were somehow absent.

## What is _not_ allowed to fall back

`partners.eligibility.*` reason keys come from the backend and are looked up dynamically:

```tsx
{
  t(partner.eligibility.reasonKey, { defaultValue: t('partners.eligibility.unknown') });
}
```

An unrecognised key from the server must not render raw, so it gets an explicit
`defaultValue`. Same pattern for any server-supplied i18n key.

## Notes

- Missing keys are invisible at runtime by design. `npm run i18n:check` is how you see them.
- `en.json` is the baseline. A key that does not exist there does not exist at all.
