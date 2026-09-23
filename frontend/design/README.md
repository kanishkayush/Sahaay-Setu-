# design/

Mirror of the design language generated in **Open Design**, synced into this repo so it is
versioned alongside the code it is meant to change.

## Do not edit these files

They are overwritten on every sync. Edit in Open Design, then re-sync:

```bash
bash .agents/sync-design.sh
```

`MANIFEST.json` records the source project, sync time, a checksum and the screen list.

## Why it lives here

Open Design writes to its own sandbox under `~/Library/Application Support/Open Design/`,
which is invisible to git, to reviewers, and to any agent working in this repo. Mirroring it
in means the design can be diffed, reviewed and discussed in the same place as the code.

## What these are — and are not

HTML/CSS **mockups**, one per screen per platform. They are a design reference, not shippable
code. Porting anything from here into the app is a deliberate step: tokens go to
`src/theme/index.ts`, structure into the components under `src/components/`.

## Before porting anything, check it against the accessibility floor

Several decisions in this app are constraints, not taste. A design pass optimising for looks
can undo them silently, and they are the difference between usable and unusable for the people
this app is for — often first-time smartphone users, on cheap Android devices, outdoors, making
a real financial decision.

| Constraint | Where it is recorded |
|---|---|
| Touch targets ≥ 48dp | `.agents/skills/sahaay-frontend/references/a11y-touch-and-contrast.md` |
| Body text ≥ 16px, nothing below 13px | same |
| Contrast ≥ WCAG AA | same |
| Status never signalled by colour alone | same |
| Indic-aware line heights | `references/ui-indic-typography.md` |
| Steppers, not drag sliders | ADR-007 in `context/decisions.json` |
| Unverified data keeps its warning | ADR-009, `references/honesty-unverified-data.md` |

A mockup that breaks one of these is a mockup to push back on, not a spec to implement.
