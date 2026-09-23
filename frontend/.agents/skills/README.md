# Project skills

Task-specific playbooks in the Anthropic skill format. Claude Code loads a `SKILL.md`
directly; every other tool can read them as plain Markdown.

Each skill follows the same shape:

```
<skill-name>/
├── SKILL.md          entry point — principles, rules table, when to apply
├── CHANGELOG.md      what changed and when
└── references/       one file per rule, loaded on demand
    ├── _template.md      copy this to add a rule
    └── <prefix>-<topic>.md
```

**Progressive disclosure is the point.** `SKILL.md` is short enough to read every time and
carries the rules an agent must never get wrong. The `references/` files hold the detail —
each one a single rule with a wrong example, a right example, and why it matters — and are
read only when that rule is in play. Do not inline reference content back into `SKILL.md`.

## Skills

| Skill                                                 | Load before                                                       |
| ----------------------------------------------------- | ----------------------------------------------------------------- |
| [`sahaay-frontend`](sahaay-frontend/SKILL.md)         | Writing or changing any screen or component                       |
| [`api-contract-change`](api-contract-change/SKILL.md) | Touching `src/api/contracts/`, services, or the mock              |
| [`scheme-domain`](scheme-domain/SKILL.md)             | Writing eligibility, recommendation, EMI or partner-routing logic |
| [`add-a-language`](add-a-language/SKILL.md)           | Adding a language or extending translations                       |

## Adding a rule to an existing skill

1. Copy `references/_template.md` to `references/<prefix>-<topic>.md`
2. Fill it in — a rule with no wrong/right pair is not yet a rule
3. Add the row to the rules table in that skill's `SKILL.md`
4. Note it in that skill's `CHANGELOG.md`

## Adding a new skill

Only when a task type is recurring and has rules an agent gets wrong without them. A skill
that just restates the README is noise. Follow the directory shape above, and add it to the
table here, to `.agents/PROTOCOL.md` §10, and to `CLAUDE.md`.
