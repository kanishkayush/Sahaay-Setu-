# rule-women-rates

**Where a scheme offers a women's concessional rate, apply it automatically. Some schemes are
women-only; those exclude other applicants outright.**

## Why it matters

Women's concessional rates are a deliberate policy instrument, and the difference is material —
5% instead of 6.5% on a ₹2 lakh loan over five years is real money. A user should never have to
know the rate exists to receive it.

The two mechanisms are distinct and both must be handled: `eligibleGender` restricts _who_
qualifies, `womenInterestRatePct` changes the _rate_ for those who do.

## Wrong

```ts
const rate = scheme.interestRateMinPct; // ← silently overcharges every woman
```

```ts
// treating the restriction as a preference
if (scheme.eligibleGender === 'FEMALE' && profile.gender === 'FEMALE') score += 15;
// → a man still sees Mahila Samriddhi Yojana in his results
```

## Right

```ts
export function applicableRate(scheme: Scheme, profile: ApplicantProfile): number {
  if (profile.gender === 'FEMALE' && scheme.womenInterestRatePct !== undefined) {
    return scheme.womenInterestRatePct;
  }
  return scheme.interestRateMinPct;
}
```

```ts
if (scheme.eligibleGender !== 'ANY') {
  if (!profile.gender) {
    blockers.push(reason('INFO',
      'This scheme is for women beneficiaries — tell us your gender to check', …));
  } else if (profile.gender !== scheme.eligibleGender) {
    blockers.push(reason('MISMATCH', 'Reserved for women beneficiaries', …));
  } else {
    score += 15;
    reasons.push(reason('MATCH',
      'Reserved for women — you get the lowest concessional rate', …));
  }
}
```

Three cases, not two. **Unknown gender is not a rejection** — it is an invitation to answer the
optional question, phrased as `INFO` rather than `MISMATCH`.

## Gender is optional, and the copy says why

The wizard's fifth step is optional and explains itself: _"Some schemes offer women a lower
interest rate."_ Asking for a demographic attribute without saying what it is for is both worse
UX and worse practice. A user who skips it still gets recommendations — just not the women-only
ones.

## Verified

```
Woman artisan, ₹1,20,000 project, ₹2,00,000 income
→ NSFDC-SSY (82) ₹1,08,000 @5%    ← women's rate, not the 6% base
→ NSFDC-MSY (77) ₹1,08,000 @5%    ← women-only scheme
→ NSFDC-MKY (77) ₹1,08,000 @5%

Same profile as male
→ MSY and MKY appear in nearMisses: "Reserved for women beneficiaries"
```

## Notes

- The UI surfaces the rate independently of the recommender, via a chip on `SchemeCard`:
  `t('schemes.womenRate', { rate })`.
- `BeneficiaryGenderSchema` includes `OTHER`. Current schemes use `FEMALE` or `ANY`; a scheme
  restricted to `OTHER` would work without engine changes.
- The rate is per-scheme data. Never hardcode 5%.
