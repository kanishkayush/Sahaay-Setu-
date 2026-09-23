# rule-funding-share

**Eligible loan = `min(projectCost × fundingSharePct, scheme.maxLoanAmount)`. Both limits bind
independently.**

## Why it matters

Two separate caps, and people conflate them. The scheme funds up to 90% of the project — so the
beneficiary must arrange the remaining 10% as margin money — _and_ the scheme has an absolute
ceiling regardless of project size. A ₹50 lakh project under a scheme capped at ₹1.40 lakh gets
₹1.40 lakh, not ₹45 lakh.

Telling someone they qualify for more than they will receive sends them to a branch expecting
one number and hearing another.

## Wrong

```ts
const loan = projectCost * 0.9; // ← ignores the ceiling
const loan = Math.min(projectCost, scheme.maxLoanAmount); // ← ignores the 90% share
const loan = projectCost * scheme.fundingSharePct; // ← still ignores the ceiling
```

## Right

```ts
export function eligibleLoanAmount(
  projectCost: number,
  fundingSharePct: number,
  schemeMaxLoan: number,
): number {
  return Math.max(0, Math.min(Math.floor(projectCost * fundingSharePct), schemeMaxLoan));
}
```

## Verified

```
eligibleLoanAmount(1_000_000, 0.9, 140_000)  → 140_000   (capped by ceiling)
eligibleLoanAmount(  100_000, 0.9, 140_000)  →  90_000   (capped by share)
```

## Surfacing it

Which cap bound the answer changes what the user should do, so the UI says:

```ts
const uncapped = Math.floor(projectCost * scheme.fundingSharePct);
const coverage = uncapped === 0 ? 0 : loan / uncapped;

if (coverage >= 0.999) {
  // "Covers 90% of your project — ₹1,26,000"
} else {
  // "Caps at ₹1,40,000, so you would need to arrange the rest"
}
```

`coverage` also feeds the score, so a scheme that covers the full share ranks above one that
truncates the project.

## Notes

- `fundingSharePct` is 0–1 in the contract (`0.9`), displayed as a percentage. Do not store 90.
- `Math.floor`, not `round` — never quote a rupee more than the scheme will actually sanction.
- **Margin money** — the beneficiary's own contribution, `projectCost − loanAmount` — is not
  yet surfaced anywhere in the UI. It is often the reason an application stalls, so showing it
  on the results and scheme-detail screens is a worthwhile addition. There is deliberately no
  helper for it in `emi.ts` until something renders it.
