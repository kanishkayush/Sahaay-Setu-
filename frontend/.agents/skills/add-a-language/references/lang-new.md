# lang-new

**Five steps, three files. Nothing else needs touching — the picker, the profile screen and the
assistant all read `SUPPORTED_LANGUAGES`.**

## Steps

### 1. The locale file

`src/i18n/locales/<code>.json`. Copy `en.json` and translate what you can. A partial file is
fine — see `lang-fallback.md`.

```jsonc
{
  "_meta": {
    "coverage": "partial",
    "note": "Untranslated keys fall back to English. Run `npm run i18n:check` to see the gap.",
  },
  "common": { "appName": "…", "continue": "…" },
  "language": { "en": "English", "hi": "हिन्दी" /* … every language, in its own script */ },
  "nav": { "home": "…", "schemes": "…" },
}
```

Keys starting with `_` are ignored by the coverage checker, so `_meta` is free.

### 2. The API contract

```ts
// src/api/contracts/common.ts
export const LanguageCodeSchema = z.enum(['en', 'hi', 'mr', 'bn', 'ta', 'te', 'kn']);
```

This is what lets the backend receive it as `responseLanguage`. **Tell the backend teammate** —
this is a shared contract change.

### 3. Register it

```ts
// src/i18n/index.ts
import kn from './locales/kn.json';

export const resources = { /* … */ kn: { translation: kn } } as const;

export const SUPPORTED_LANGUAGES: LanguageOption[] = [
  // …
  { code: 'kn', endonym: 'ಕನ್ನಡ', englishName: 'Kannada' },
];
```

**`endonym` is the language's name in its own script, and is never translated.** A user who
cannot read English must still be able to find their language.

### 4. Add its name to every other locale

Each locale's `language` block lists all languages, so the picker reads correctly whichever
language is active. Add `"kn": "ಕನ್ನಡ"` to `en.json`, `hi.json`, and the rest.

### 5. Check

```bash
npm run i18n:check
npm run verify
```

Then look at it on a device — see `lang-script-rendering.md`.

## Wrong

```ts
{ code: 'kn', endonym: 'Kannada', englishName: 'Kannada' }   // ← endonym in Latin
```

```ts
// forgetting LanguageCodeSchema — the UI switches but the AI keeps answering in English
```

## Notes

- Which languages to prioritise follows the beneficiary population, not speaker counts
  generally — this is an SC-focused scheme, so state-level SC demographics matter more.
- No custom font is bundled. System fonts have the widest Indic coverage on cheap Android
  devices; a webfont missing a glyph renders tofu.
- `deviceLanguage()` picks up the new locale automatically if the device is set to it.
