# honesty-unverified-data

**Unverified data renders its warning. Ungrounded AI answers render their caveat. Never remove
either to make a screen look cleaner.**

## Why it matters

Three schemes carry `verified: false` — they appear on `nsfdc.nic.in` but their current
figures could not be read from an official page. Every Channel Partner carries
`status: 'UNKNOWN'`, because NSFDC publishes its eligibility norms but not the per-partner
figures behind them. The assistant's offline fallback is keyword matching, not a model.

Each of those states has a UI treatment, and each treatment is load-bearing. `verified: false`
renders a warning; `UNKNOWN` renders as an explicit "fund status not reported" rather than as
a neutral-looking blank; an ungrounded answer renders its caveat.

The people using this app are making real financial decisions with real consequences. A
polished screen that presents an unchecked loan term as authoritative is the worst thing this
project could ship. Looking visibly honest about what is not known is strictly better than
looking finished.

This is the single rule most likely to be "tidied away" before a demo. Do not.

## Wrong

```tsx
// dropping the chip because it clutters the card
<Card>
  <Text variant="subheading">{name}</Text>
  <Chip label={t(`category.${scheme.category}`)} tone="primary" />
</Card>

// rendering an ungrounded answer as if it were confident
<Text>{response.answer}</Text>
```

## Right

```tsx
{
  !scheme.verified ? <Chip label={t('common.unverified')} tone="warning" prefix="⚠" /> : null;
}
```

```tsx
{
  !response.grounded ? <Banner tone="warning" message={t('assistant.ungrounded')} /> : null;
}
```

```tsx
// catalogue-level disclaimer, when the API sends one
{
  data?.dataDisclaimer ? (
    <Banner tone="warning" message={pickLocalized(data.dataDisclaimer, language)} />
  ) : null;
}
```

## The flags and what they drive

| Flag                                        | Source                            | UI                                        |
| ------------------------------------------- | --------------------------------- | ----------------------------------------- |
| `Scheme.verified === false`                 | per-scheme, from the catalogue    | warning chip on cards, banner on detail   |
| `SchemeListResponse.dataDisclaimer`         | catalogue-level                   | banner above the list                     |
| `AssistantQueryResponse.grounded === false` | the RAG layer's own confidence    | "confirm with a Channel Partner" caveat   |
| `RecommendationResponse.offline === true`   | backend unreachable, rules used   | "offline result" chip                     |
| `PartnerSearchResponse.fallbackUsed`        | every nearby partner is unhealthy | warning explaining why                    |
| `USE_MOCK_API === true`                     | app config                        | prototype-data banner on Home and Profile |

## Notes

- `verified` flips to true **per scheme**, as each is individually confirmed — never all at
  once as a batch edit.
- Fixture files carry loud header comments. Keep them; they are the warning for the next
  developer, the way the chips are the warning for the user.
- ADR-009 records this decision.
- If a demo needs to look cleaner, the fix is to verify the data, not to hide the label.
