# rule-ticket-size

**Ticket size selects the product family: micro-finance to ~₹1.40 lakh, term loan above that to
₹50 lakh. A technically-eligible but badly-sized scheme must rank low, not appear first.**

## Why it matters

The brief names this as the core confusion: people cannot distinguish a Micro Finance Scheme for
small projects from a Term Loan for larger ones. A recommender that ranks by interest rate alone
would offer a ₹1.40 lakh micro-loan for a ₹20 lakh manufacturing unit — eligible on paper,
useless in practice, and exactly the misrouting the platform exists to prevent.

## The families

| Family                                                       | Range                 | Typical purpose                                   |
| ------------------------------------------------------------ | --------------------- | ------------------------------------------------- |
| `MICRO_FINANCE`                                              | ₹10k – ₹1.40 lakh     | vending, petty trade, tiny self-employment        |
| `TERM_LOAN`                                                  | ₹1.40 lakh – ₹50 lakh | manufacturing, transport, service ventures        |
| `EDUCATION_LOAN`                                             | ₹50k – ₹40 lakh       | course fees (see `rule-education-exclusivity.md`) |
| `WOMEN_SPECIFIC`, `ARTISAN`, `AGRICULTURE`, `GREEN_MOBILITY` | narrower              | purpose-specific, mostly micro-sized              |

## Wrong

```ts
// rate alone
return schemes.sort((a, b) => a.interestRateMinPct - b.interestRateMinPct);
// → a ₹1.4L micro-credit scheme at 5% tops the list for a ₹20L factory
```

```ts
// hard-excluding anything not perfectly sized
if (projectCost > scheme.maxLoanAmount) return [];
// → too aggressive; a partial loan is sometimes genuinely useful
```

## Right

Exclude only when the project is below the scheme's floor; otherwise let coverage and category
fit drive the ranking.

```ts
if (loan < scheme.minLoanAmount) {
  blockers.push(reason('MISMATCH',
    `Your project is too small — this scheme starts at ${formatInr(scheme.minLoanAmount)}`, …));
} else {
  const coverage = loan / Math.floor(projectCost * scheme.fundingSharePct);
  score += Math.round(30 * coverage);     // truncated coverage scores lower
}

const preferred = CATEGORY_BY_PROJECT_TYPE[profile.projectType] ?? [];
const idx = preferred.indexOf(scheme.category);
if (idx === 0) score += 20;               // purpose-built for this activity
else if (idx > 0) score += 10;
```

## Verified

```
₹20,00,000 manufacturing, ₹4,00,000 income
→ NSFDC-TL   (81) loan ₹18,00,000 @6.5%     ← term loan, full coverage
→ NSFDC-LVY  (59) loan   ₹5,00,000 @6%
→ NSFDC-MCF  (43) loan   ₹1,40,000 @6%      ← eligible, correctly ranked last-ish

₹80,000 street vending, ₹1,20,000 income
→ NSFDC-MCF  (81) loan ₹72,000 @6%          ← micro-finance first
```

## Notes

- The score is a blend: income gate 25, gender 15, coverage 30, category fit 20, rate up to 10.
  Coverage and category together outweigh rate, which is what keeps sizing sensible.
- `CATEGORY_BY_PROJECT_TYPE` maps a project type to an ordered list of categories. Index 0 is
  "purpose-built", later entries are "acceptable". Add new project types there.
- The ₹1.40 lakh boundary comes from the scheme data, not a constant. Read it from
  `minLoanAmount` / `maxLoanAmount`.
