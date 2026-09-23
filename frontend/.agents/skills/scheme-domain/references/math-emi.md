# math-emi

**Reducing-balance EMI on integer rupees. The moratorium changes the amortised principal, not
just the start date.**

## Why it matters

This is the number the user plans their life around. It must be right, it must work offline,
and it must handle the moratorium correctly — because interest accrues during the repayment
holiday, and most people assume it does not.

`src/features/calculator/emi.ts` is pure: no React, no network, no imports. Keep it that way
(ADR-005) so it stays trivially verifiable and reusable.

## The formula

```
EMI = P · r · (1+r)^n / ((1+r)^n − 1)      r = annualRate / 12 / 100
```

with `r = 0` handled separately — `P/n`, since the general form divides by zero.

```ts
export function calculateFlatEmi(principal: number, annualRatePct: number, tenureMonths: number) {
  if (tenureMonths <= 0) throw new RangeError('tenureMonths must be greater than 0');
  if (principal <= 0) return 0;

  const r = monthlyRate(annualRatePct);
  if (r === 0) return principal / tenureMonths;

  const growth = Math.pow(1 + r, tenureMonths);
  return (principal * r * growth) / (growth - 1);
}
```

## Known-good values

Check any change against these:

| Input                                               | Expected                                                           |
| --------------------------------------------------- | ------------------------------------------------------------------ |
| ₹1,00,000 @ 10% × 12mo                              | **8791.59** (textbook)                                             |
| ₹60,000 @ 0% × 12mo                                 | 5000.00                                                            |
| ₹2,00,000 @ 6.5% × 60mo, 6mo moratorium capitalised | principal grows to ₹2,06,589; EMI ₹4,042; 66 rows; total ₹2,42,520 |
| same, interest serviced monthly                     | principal stays ₹2,00,000; EMI ₹3,913; total ₹2,41,278             |
| ₹1,26,000 @ 5% × 48mo, 3mo moratorium capitalised   | EMI ₹2,938; total ₹1,41,024 (= 48 × 2938)                          |
| tenure 0                                            | throws `RangeError`                                                |

Every schedule must close at a **zero** balance, and `totalPayable` must equal the sum of
every row's `emi` — that is the invariant, not `principal + totalInterest`, which drifts by a
few rupees of rounding and omits capitalised moratorium interest.

## The moratorium is the part people get wrong

3–12 months with no EMI due — but interest still accrues. Two treatments, and they produce
different answers:

**`CAPITALISE`** (default, and how education loans usually work): accrued interest is added to
the principal, so the post-holiday EMI is higher.

```ts
const interest = balance * r;
moratoriumInterest += interest;
balance = balance + interest; // ← the principal actually grows
```

**`SERVICE_MONTHLY`**: the borrower pays interest each month during the holiday, principal
untouched.

```ts
const interest = balance * r;
moratoriumInterest += interest;
// balance unchanged; the payment is recorded as this month's EMI
```

Then `amortisedPrincipal = balance` — which is _not_ the original principal under capitalisation.
That is the subtlety.

## Wrong

```ts
// treating the moratorium as a delay
const emi = calculateFlatEmi(principal, rate, tenure);
const firstDueMonth = moratoriumMonths + 1;
// → understates the EMI; the accrued interest vanished
```

```ts
// float money accumulating drift over 120 rows
let balance = 200000.0;
// → the final balance lands at 0.0000003 instead of 0
```

## Right

Round only at the boundary, and let the final instalment absorb the drift:

```ts
const isLast = m === tenureMonths;
const principalComponent = isLast ? balance : emi - interest;
const payment = isLast ? balance + interest : emi;
const closing = isLast ? 0 : balance - principalComponent;
```

## Notes

- All display rounding goes through `round()` at assembly time; internal arithmetic keeps full
  precision.
- The schedule marks moratorium rows with `isMoratorium: true` so the UI can highlight them.
- **`totalPayable` is derived from the schedule** (`schedule.reduce((s, r) => s + r.emi, 0)`),
  not computed from the component figures. Two reasons. First, the headline total must equal
  the instalments the user can see and add up — summing independently rounded components
  drifts by a few rupees and reads as an error. Second, an earlier version computed
  `principal + totalInterest + servicedMoratoriumInterest`, which **understated** the total
  under `CAPITALISE`: capitalised interest lives in the _principal_, not in `totalInterest`,
  so excluding it lost it entirely. Deriving from the schedule makes that class of bug
  impossible.
- The regression invariant to keep: `totalPayable === sum of every row's emi`, in both
  treatments, with and without a moratorium.
- Rate range in the UI is 4–15%, moratorium 0–12 months, tenure 6–120 months, matching the
  brief.
