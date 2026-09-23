---
name: sahaay-frontend
description: 'Use when writing or changing ANY screen, component, hook or style in the Sahaay Setu React Native app. Triggers: adding or editing files under app/ or src/components/ or src/hooks/; adding a route; building a form or input; rendering scheme, partner or recommendation data; styling anything; adding user-visible text; fixing layout, overflow or font-scaling issues; accessibility work; anything involving money display or Indic-script rendering. Load this BEFORE writing the file, not after — several of these rules (the data-flow boundary, the Text component, hardcoded strings) are expensive to retrofit.'
license: MIT
metadata:
  project: sahaay-setu
  version: '1.0.0'
  updated: 2026-09-07
  abstract: >
    Frontend conventions for a multilingual React Native app used by first-time smartphone
    owners on low-cost Android devices, outdoors, on poor connectivity, while making a real
    financial decision. Rules span architecture (one-directional data flow), i18n (two
    distinct kinds of translatable text), theming, Indic typography, accessibility floors,
    and honesty about unverified data.
---

# Sahaay Setu frontend

## Who this app is for

Often first-time smartphone users, on low-cost Android devices, in bright sunlight, with
patchy connectivity, making a financial decision that affects their livelihood.

Every rule below follows from that sentence. None of it is stylistic preference, and none of
it should be relaxed to make a screenshot look tidier.

## Core principles

**1. The data-flow boundary is one-directional and absolute.**
`screen → hook → service → mock or HTTP`. A screen never imports `src/api/mock/` and never
calls `fetch`. This is what lets the entire app switch to the real backend by flipping one env
var. If you need data a service does not expose, add a function to the service — do not reach
around it. → `references/flow-data-layer.md`

**2. Nothing user-visible is hardcoded.**
Every string goes through `t()` into `src/i18n/locales/en.json`. Every colour and spacing value
comes from `@/theme`. There are no exceptions for "temporary" or "debug" UI — those ship.
→ `references/i18n-strings.md`, `references/ui-theming.md`

**3. Use `Text` from `@/components/ui`, never react-native's.**
Ours carries the line heights Devanagari, Bengali, Tamil and Telugu need. Latin-tuned leading
clips these scripts — the descenders and matras get cut. → `references/ui-indic-typography.md`

**4. The accessibility floor is a constraint, not a polish pass.**
48dp touch targets, 16px body text, WCAG AA contrast, and status never conveyed by colour
alone. → `references/a11y-touch-and-contrast.md`

**5. Degrade, never fail.**
No map module → list view. No backend → on-device rules. No translation → English. The user
always gets something usable. → `references/flow-degradation.md`

**6. Never dress up unverified data.**
A scheme with `verified: false` must render its warning. An ungrounded AI answer must show its
caveat. Do not remove these to make a demo look cleaner — see ADR-009.
→ `references/honesty-unverified-data.md`

## When to apply

Load this skill before:

- Adding or editing anything under `app/`, `src/components/`, `src/hooks/`
- Adding a route or changing navigation
- Building any form, input or numeric control
- Rendering scheme, partner or recommendation data
- Any styling, layout or overflow work
- Adding user-visible text of any kind
- Accessibility work
- Anything displaying money

## Rules

| Prefix     | Rule                                                        | Read when                                        |
| ---------- | ----------------------------------------------------------- | ------------------------------------------------ |
| `flow-`    | [data-layer](references/flow-data-layer.md)                 | Fetching or mutating anything                    |
| `flow-`    | [new-screen](references/flow-new-screen.md)                 | Adding a route                                   |
| `flow-`    | [state-placement](references/flow-state-placement.md)       | Deciding where state lives                       |
| `flow-`    | [degradation](references/flow-degradation.md)               | A dependency might be missing at runtime         |
| `i18n-`    | [strings](references/i18n-strings.md)                       | Adding user-visible text                         |
| `i18n-`    | [localized-content](references/i18n-localized-content.md)   | Rendering backend content (scheme names, labels) |
| `ui-`      | [theming](references/ui-theming.md)                         | Any colour, spacing or radius                    |
| `ui-`      | [indic-typography](references/ui-indic-typography.md)       | Any text rendering                               |
| `a11y-`    | [touch-and-contrast](references/a11y-touch-and-contrast.md) | Any interactive element                          |
| `a11y-`    | [inputs](references/a11y-inputs.md)                         | Any form control                                 |
| `money-`   | [formatting](references/money-formatting.md)                | Displaying an amount                             |
| `honesty-` | [unverified-data](references/honesty-unverified-data.md)    | Rendering scheme or AI data                      |

## Verify before you claim

```bash
npm run verify                        # typecheck + lint + i18n coverage
npx expo export --platform android    # the only real check of the import graph
```

A screen that typechecks can still fail to bundle. If you touched imports, navigation or a
native module, the export is not optional.

Then checkpoint what you verified, with the command that proves it:

```bash
bash .agents/checkpoint.sh save --agent <you> --task "..." \
  --verified "fact=the command you ran and what it printed"
```
