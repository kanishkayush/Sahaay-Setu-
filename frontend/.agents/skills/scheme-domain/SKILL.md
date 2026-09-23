---
name: scheme-domain
description: "Use when writing or changing any logic that decides money or eligibility. Triggers: editing src/features/recommender/ or src/features/calculator/; changing scheme fixtures or the scheme catalogue; anything involving income ceilings, loan limits, interest rates, moratoria, EMI or amortisation; partner routing, NPA or fund-utilisation filtering; adding a scheme or a scheme category; writing copy that states a loan figure. Read this BEFORE writing the logic — these are domain rules from India's channel finance system, not conventions, and getting one wrong puts a wrong number in front of someone making a real financial decision."
license: MIT
metadata:
  project: sahaay-setu
  version: '1.0.0'
  updated: 2026-09-07
  abstract: >
    Domain rules for NSFDC-style concessional credit routed through India's Channel Finance
    System. Covers the ₹5 lakh income ceiling, the 90% funding share, ticket-size product
    families, women's concessional rates, education-loan exclusivity, partner fund-health
    routing, and the EMI/moratorium mathematics — each mapped to the code that implements it.
---

# Scheme and channel-finance domain

An agent unfamiliar with Indian channel finance will produce plausible-looking logic that is
wrong. Read this first.

## The system in four sentences

The government offers concessional credit to Scheduled Caste beneficiaries — up to 90% of
project cost at 5–8% a year, for families earning under ₹5 lakh. **You cannot apply directly.**
Funds route through 100+ Channel Partners: State Channelizing Agencies (SCA), Public Sector
Banks (PSB), Regional Rural Banks (RRB), and NBFC-MFIs. Which scheme fits depends mostly on
ticket size and purpose; which partner can help depends on their authorisation _and_ whether
their fund position lets them disburse at all.

Full glossary: `context/domain.json`.

## Core rules

**1. ₹5,00,000 annual family income is a hard ceiling.**
Not a scoring signal — a gate. Above it, nothing is recommended, and the reason is shown.
→ `references/rule-income-ceiling.md`

**2. Loan = min(projectCost × fundingSharePct, scheme ceiling).**
The 90% share and the per-scheme cap are two separate limits and both bind.
→ `references/rule-funding-share.md`

**3. Ticket size selects the product family.**
Micro-finance to ~₹1.40 lakh; term loan above that to ₹50 lakh. Recommending a ₹1.4 lakh
micro-loan for a ₹20 lakh project is technically valid and practically useless.
→ `references/rule-ticket-size.md`

**4. Education loans are only for education, and business loans only for business.**
A hard gate in both directions. → `references/rule-education-exclusivity.md`

**5. Women get the lower rate where a scheme offers one.**
Some schemes are women-only; several offer a reduced rate. Apply it automatically.
→ `references/rule-women-rates.md`

**6. Never route to a partner that cannot disburse.**
High NPAs or exhausted funds mean the application stalls. This filter is the entire point of
requirement R3. → `references/rule-partner-routing.md`

**7. Money math is integer rupees, reducing balance, and the moratorium changes the principal.**
→ `references/math-emi.md`

**8. Every figure in this repo is unverified. Say so.**
→ `references/data-honesty.md`

## Rules

| Prefix  | Rule                                                              | Implemented in                   |
| ------- | ----------------------------------------------------------------- | -------------------------------- |
| `rule-` | [income-ceiling](references/rule-income-ceiling.md)               | `ruleEngine.ts` hard gate 1      |
| `rule-` | [funding-share](references/rule-funding-share.md)                 | `emi.ts` `eligibleLoanAmount`    |
| `rule-` | [ticket-size](references/rule-ticket-size.md)                     | scheme min/max + scoring         |
| `rule-` | [education-exclusivity](references/rule-education-exclusivity.md) | `ruleEngine.ts` hard gate 3      |
| `rule-` | [women-rates](references/rule-women-rates.md)                     | `ruleEngine.ts` `applicableRate` |
| `rule-` | [partner-routing](references/rule-partner-routing.md)             | `mock/server.ts`, backend        |
| `math-` | [emi](references/math-emi.md)                                     | `features/calculator/emi.ts`     |
| `data-` | [honesty](references/data-honesty.md)                             | fixtures + `verified` flag       |

## Explainability is a requirement, not a nicety

The brief names financial literacy as the problem. A recommendation that cannot say _why_ has
not met it. Every `SchemeRecommendation` carries `reasons[]`, and every excluded scheme carries
the blocker that excluded it — `nearMisses` is often more useful than the match list, because
"your family income is above the ₹5 lakh limit" is actionable information.

When adding a rule, add its user-facing explanation in the same commit, in `en` and `hi`.

## Verify with real numbers

Domain logic is pure and directly runnable:

```bash
node --experimental-strip-types -e "
  import('./src/features/calculator/emi.ts').then(m =>
    console.log(m.calculateFlatEmi(100000, 10, 12)))   // → 8791.59
"
```

Known-good values to check against are in `references/math-emi.md`. Record what you verified
in your checkpoint, with the numbers.
