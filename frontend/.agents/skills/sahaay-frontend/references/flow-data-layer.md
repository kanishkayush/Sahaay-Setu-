# flow-data-layer

**A screen never imports from `src/api/mock/` and never calls `fetch`. Data reaches a screen
only as `screen → hook → service`.**

## Why it matters

The whole app switches from mock data to the real backend by flipping one env var
(`EXPO_PUBLIC_USE_MOCK_API`). That only works because `USE_MOCK_API` is checked in exactly one
place per endpoint — the service. A single screen that imports a fixture directly, or calls
`fetch` itself, silently keeps showing mock data after integration, and nobody notices until a
demo.

It also means the backend teammate can be unblocked without touching any screen.

## Wrong

```tsx
// app/(tabs)/schemes.tsx
import { MOCK_SCHEMES } from '@/api/mock/fixtures/schemes'; // ← bypasses the switch

export default function SchemesScreen() {
  const [schemes] = useState(MOCK_SCHEMES);
  // ...
}
```

```tsx
// also wrong — no validation, no mock branch, no caching
const res = await fetch(`${API_BASE_URL}/v1/schemes`);
const data = await res.json();
```

## Right

```tsx
// app/(tabs)/schemes.tsx
import { useSchemes } from '@/hooks/useSchemes';

export default function SchemesScreen() {
  const { data, isLoading, isError } = useSchemes();
  // ...
}
```

The chain behind it:

```
src/hooks/useSchemes.ts        React Query, cache policy
  └─ src/api/services/schemes.service.ts    if (USE_MOCK_API) … else apiRequest(…)
       ├─ src/api/mock/server.ts
       └─ src/api/client.ts    fetch + Zod validation
```

## Notes

- If a screen needs data no service exposes, **add a function to the service**. Reaching around
  the layer is never the answer.
- `src/api/client.ts` is the only file in the app allowed to call `fetch`.
- Pure computation is different and does not go through this chain — `src/features/calculator`
  and `src/features/recommender` are imported directly, because they are local functions, not
  data sources.
- ADR-003 records why the mock ships inside the app.
