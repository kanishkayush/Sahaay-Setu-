---
name: add-a-language
description: "Use when adding a new language to the app, extending a partial translation, or fixing anything language-related. Triggers: 'add Kannada/Gujarati/Punjabi/Odia', editing src/i18n/, editing any file in src/i18n/locales/, npm run i18n:check failing, text overflowing or clipping in a non-Latin script, a raw i18n key rendering on screen, LanguageCodeSchema changes, or reviewing a translation PR. Partial translations are safe to ship — English is the fallback for every key — so this is a low-risk, high-value contribution path."
license: MIT
metadata:
  project: sahaay-setu
  version: '1.0.0'
  updated: 2026-09-07
  abstract: >
    Adding and extending languages in a six-language React Native app where English is the
    guaranteed fallback. Covers the five-step add procedure, the coverage checker's
    fail-vs-warn semantics, interpolation placeholders, endonyms, and the script-rendering
    checks that catch clipping and overflow in Indic scripts.
---

# Adding a language

Six ship today: **English, हिन्दी, मराठी, বাংলা, தமிழ், తెలుగు**. Adding a seventh takes about
fifteen minutes.

## Core principles

**1. English is the fallback for every key, always.**
A locale may be 20% translated and still ship. A missing key renders readable English, never a
raw key. This is what lets translations land incrementally without ever breaking a build
(ADR-006). → `references/lang-fallback.md`

**2. Endonyms are never translated.**
A language's name appears in its own script — मराठी, not "Marathi". A user who cannot read
English must still find their language on the picker. → `references/lang-new.md`

**3. Placeholders are code.**
`{{count}}`, `{{rate}}`, `{{months}}` must survive translation intact. Translate around them.
→ `references/lang-placeholders.md`

**4. The coverage check warns on missing, fails on unknown.**
Missing keys are expected. A key that exists in a locale but not in `en.json` is a typo or a
leftover from a rename, and that fails the build. → `references/lang-coverage.md`

**5. Check the script, not just the strings.**
Indic scripts need vertical room and produce longer strings. Tab bars and buttons break first.
→ `references/lang-script-rendering.md`

## When to apply

Adding a language, extending a partial one, reviewing a translation PR, or debugging text that
renders wrongly in a non-Latin script.

## Rules

| Prefix  | Rule                                                    | Read when                                   |
| ------- | ------------------------------------------------------- | ------------------------------------------- |
| `lang-` | [new](references/lang-new.md)                           | Adding a language — the five steps          |
| `lang-` | [extend](references/lang-extend.md)                     | Filling in a partial locale                 |
| `lang-` | [fallback](references/lang-fallback.md)                 | Understanding what happens to a missing key |
| `lang-` | [placeholders](references/lang-placeholders.md)         | Any string with interpolation or plurals    |
| `lang-` | [coverage](references/lang-coverage.md)                 | `npm run i18n:check` failed                 |
| `lang-` | [script-rendering](references/lang-script-rendering.md) | Text clips, overflows, or looks wrong       |

## Current coverage

```bash
npm run i18n:check
```

```
i18n coverage — baseline en.json has 231 keys
  bn   20%  (185 missing)
  hi  100%  (0 missing)
  mr   20%  (185 missing)
  ta   20%  (185 missing)
  te   20%  (185 missing)
```

Filling in `mr`, `bn`, `ta`, `te` is tracked as N4 in `context/state.json` and is the single
best contribution someone with the language can make.

## The AI answers in the same language

The chosen language is sent as `responseLanguage` on every assistant request and `language` on
every recommendation request. A user may type Hindi while the UI is Tamil — the answer follows
the UI, not the query. Adding a language to `LanguageCodeSchema` is what makes the backend able
to receive it.
