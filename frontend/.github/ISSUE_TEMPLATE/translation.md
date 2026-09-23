---
name: Translation
about: Add or improve a language
title: '[i18n] '
labels: i18n, good first issue
---

## Language

<!-- Code and endonym, e.g. `mr` — मराठी -->

## Adding a new language or extending an existing one?

Run `npm run i18n:check` to see current coverage.

## Notes

<!-- Anything context-dependent: financial terms with no clean translation, strings that
     overflow, script rendering issues. -->

## Before opening the PR

- [ ] Interpolation placeholders (`{{count}}`, `{{rate}}`, `{{months}}`) left intact
- [ ] Endonyms not translated — a language's name stays in its own script
- [ ] `npm run i18n:check` passes
- [ ] Checked tab-bar labels and buttons for overflow

Full steps: `.agents/skills/add-a-language/SKILL.md`
