# money-formatting

**Money is whole-rupee integers. Always format through `@/utils/format` so grouping is Indian.**

## Why it matters

Two separate problems.

**Floats lose money.** `0.1 + 0.2 !== 0.3`. Interest calculations compound the error across a
120-month schedule. Every amount in the app and in the API contract is an integer number of
rupees, with rounding applied only at the display boundary.

**Western grouping is misread.** Indian numbering groups as lakh and crore: ₹1,40,000, not
₹140,000. A user scanning for "how many lakhs" reads the comma positions. Wrong grouping on a
loan amount is a real comprehension failure, not a cosmetic one.

## Wrong

```tsx
<Text>₹{amount.toLocaleString()}</Text>          // "₹140,000" — western grouping
<Text>₹{(amount / 100000).toFixed(2)}L</Text>    // ad-hoc, inconsistent
<Text>{`${rate}%`}</Text>                         // "6.50%" or "6.5%" depending on the source
const emi = principal * 0.065 / 12;               // float money
```

## Right

```tsx
import { formatCurrency, formatCompactCurrency, formatPercent, formatMonths } from '@/utils/format';

formatCurrency(140000); // "₹1,40,000"
formatCompactCurrency(140000); // "₹1.4 lakh"
formatCompactCurrency(5000000); // "₹50 lakh"
formatPercent(6.5); // "6.5%"
formatPercent(6); // "6%"      ← not "6.00%"
formatMonths(66, t('common.months'), t('common.years')); // "5 years 6 months"
```

## Which one where

| Use                     | When                                                                                  |
| ----------------------- | ------------------------------------------------------------------------------------- |
| `formatCurrency`        | Exact amounts the user acts on — EMI, total payable, schedule rows                    |
| `formatCompactCurrency` | Scanning and comparison — scheme ceilings, card summaries, presets                    |
| Both                    | `AmountInput` shows `₹1,40,000 · ₹1.4 lakh` so the digits and the magnitude both read |

## Notes

- `formatMonths` takes the translated month/year words as arguments rather than calling `t()`
  itself, so `@/utils/format` stays pure and testable.
- Parsing user input goes through `parseAmountInput`, which strips symbols and separators.
- The EMI engine rounds only at the boundary — internal arithmetic keeps full precision, and
  the final instalment absorbs the drift so the balance lands exactly on zero. See
  `scheme-domain/references/math-emi.md`.
