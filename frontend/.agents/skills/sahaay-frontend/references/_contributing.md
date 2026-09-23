# Adding a rule to this skill

1. Copy `_template.md` to `<prefix>-<topic>.md`. Use an existing prefix where one fits:
   `flow-` · `i18n-` · `ui-` · `a11y-` · `money-` · `honesty-`
2. Write the wrong/right pair first. If you cannot produce a realistic wrong example, this is
   a preference rather than a rule and does not belong here.
3. Add the row to the rules table in `SKILL.md`.
4. Note it in `CHANGELOG.md` and bump the `version` in the `SKILL.md` frontmatter.

## What belongs here

Rules an agent or new contributor gets wrong without being told, where the cost is real:
a broken build, an unreadable screen, a wrong number, a leaked assumption.

## What does not

- Anything the typechecker or linter already enforces — let the tool catch it
- General React or TypeScript advice with no Sahaay Setu specificity
- Style opinions with no user-facing consequence

Keep `SKILL.md` short. It is read every time; these files are read only when relevant.
