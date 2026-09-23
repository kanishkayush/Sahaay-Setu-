# mock-parity

**Every endpoint in `ENDPOINTS` has a mock in `src/api/mock/server.ts` returning the same
contract shape. The mock is a feature, not scaffolding.**

## Why it matters

`USE_MOCK_API` defaults to **true**. That is the mode in which the app is developed, demoed and
handed to a judge with no network. The mock is not a stopgap to delete after integration — it
is the offline demo, and it stays.

Parity also makes the mock a specification: the backend teammate can read
`src/api/mock/server.ts` and see exactly what a valid response looks like.

## Wrong

```ts
// service with no mock branch
export async function getApplicationStatus(id: string) {
  return apiRequest(ENDPOINTS.applications.status(id), ApplicationStatusSchema);
}
// → with USE_MOCK_API=true this hits http://localhost:8000 and fails
```

```ts
// mock that drifts from the contract
export async function mockSearchPartners() {
  return { items: MOCK_PARTNERS }; // ← missing fallbackUsed, radiusKm
}
// → passes in mock mode, fails Zod against the real backend
```

## Right

```ts
export async function mockSearchPartners(
  req: PartnerSearchRequest,
): Promise<PartnerSearchResponse> {
  // ← the return type is the guard
  await delay();
  // …filtering…
  return { items, fallbackUsed, searchedFrom: req.location, radiusKm: req.radiusKm };
}
```

Annotating the mock with the contract type means `npm run typecheck` catches drift the moment
the schema changes.

## What a good mock does

- **Respects the request.** Filters, radius, `onlyAccepting` — if the real endpoint honours a
  parameter, the mock must too, or you will build UI against behaviour that does not exist.
- **Simulates latency** via `delay()`, so loading states are real during development.
- **Exercises the awkward paths.** Every partner fixture is `UNKNOWN` — that is the honest
  state, not a gap — so `ACCEPTING`, `LIMITED` and `NOT_ACCEPTING` are reachable only once a
  real feed exists. Until then, exercise `fallbackUsed` and the filtering from a test, not by
  inventing an NPA figure against a named real institution. See `scheme-domain/references/data-honesty.md`.
- **Reuses real logic where it exists.** `mockRecommend` calls the actual rule engine rather
  than returning canned results.

## Notes

- Screens never import `src/api/mock/` — see `sahaay-frontend/references/flow-data-layer.md`.
- Fixture files carry loud headers saying the data is invented. Keep them.
- `mockAssistantQuery` is keyword matching, not a model. It is honest about that in its header
  and returns `grounded: false` when it does not recognise a question.
