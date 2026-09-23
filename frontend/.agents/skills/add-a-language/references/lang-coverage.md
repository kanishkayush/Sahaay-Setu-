# lang-coverage

**`npm run i18n:check` warns on missing keys and fails on unknown ones. The asymmetry is
deliberate.**

## Why it matters

Missing keys are expected — partial locales are the design (ADR-006), and English covers them.
But a key present in a locale and absent from `en.json` is dead weight: a typo, or a leftover
from a rename that no longer resolves. It renders nothing and is invisible at runtime, so the
check is the only place it surfaces.

## Output

```
i18n coverage — baseline en.json has 231 keys

  bn   20%  (185 missing)
  hi  100%  (0 missing)
  mr   20%  (185 missing)
  ta   20%  (185 missing)
  te   20%  (185 missing)

Missing keys fall back to English — that is expected for partial locales.
OK
```

Failure looks like:

```
  ta   19%  (186 missing)
      ✗ 1 key(s) not in en.json: recommender.resultsTitel

FAILED: remove or rename the unknown keys listed above.
```

## Fixing a failure

| Cause                    | Fix                                                  |
| ------------------------ | ---------------------------------------------------- |
| Typo in the locale       | Correct the key to match `en.json`                   |
| Key renamed in `en.json` | Rename it in every locale too                        |
| Genuinely new string     | Add it to `en.json` **first** — that is the baseline |
| Deliberate metadata      | Prefix with `_`; keys starting with `_` are skipped  |

## Wrong

```jsonc
// adding a string only to the locale that needs it
// ta.json
{ "schemes": { "tamilOnlyNote": "…" } } // ← fails; en.json has no such key
```

```jsonc
// silencing the checker by adding an empty English string
// en.json
{ "schemes": { "tamilOnlyNote": "" } } // ← renders blank for everyone else
```

## Right

Add the real English string to `en.json`, then translate it:

```jsonc
// en.json
{ "schemes": { "regionalNote": "Availability varies by state." } }
// ta.json
{ "schemes": { "regionalNote": "…" } }
```

## In CI

`npm run verify` runs the check, so an unknown key cannot land on main. Coverage percentages
are informational and never fail a build.

## Notes

- The script is `scripts/check-i18n.mjs`, ~40 lines, no dependencies.
- It flattens nested objects to dotted paths, matching the runtime `keySeparator: '.'`.
- `_meta` blocks are skipped, which is why they are safe to use for coverage notes.
