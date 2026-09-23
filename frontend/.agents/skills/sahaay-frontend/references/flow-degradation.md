# flow-degradation

**When a dependency may be missing at runtime, degrade to something usable. Never let it crash
a screen, and never render a control that does not work.**

## Why it matters

Our users are on connectivity that drops and devices that vary. `react-native-maps` needs
native code and is absent on web and in some Expo Go clients. The backend may be down. A
translation may not exist. In every case the user should still get the core value — a crash or
a dead button is a much worse outcome than a plainer screen.

## Wrong

```tsx
// top-level import — if the native module is missing, the whole Partners tab dies
import MapView, { Marker } from 'react-native-maps';

export function PartnerMap({ partners }) {
  return <MapView>{/* … */}</MapView>;
}
```

```tsx
// a control that does nothing
<Button title="🎤 Voice input" onPress={() => alert('Coming soon')} />
```

## Right

```tsx
// src/components/domain/PartnerMap.tsx — load defensively, fall back explicitly
let maps: MapsModule | null = null;
try {
  maps = require('react-native-maps') as MapsModule;
} catch {
  maps = null;
}

export function PartnerMap({ partners, unavailableMessage }: PartnerMapProps) {
  if (!maps) {
    return (
      <View style={styles.placeholder}>
        <Text variant="caption" color={colors.textMuted} center>
          {unavailableMessage}
        </Text>
      </View>
    );
  }
  // …
}
```

## The degradation ladder in this app

| Missing                    | Falls back to                     | Flagged as                    |
| -------------------------- | --------------------------------- | ----------------------------- |
| `react-native-maps`        | List view (the primary UX anyway) | placeholder card              |
| Backend `/recommendations` | On-device rule engine             | `offline: true`               |
| Backend `/assistant/query` | Offline knowledge base            | `grounded: false`             |
| A translation key          | English                           | nothing — invisible by design |
| Network, for the catalogue | React Query cache (1h)            | nothing                       |
| Speech-to-text provider    | Typing                            | the mic is not rendered       |

Each fallback that changes the _quality_ of the answer is surfaced to the user. A missing
translation is not, because English is a correct answer.

## Notes

- **Do not build UI for a capability that does not exist.** Speech-to-text now ships, but the
  rule did not change — it moved into code. `detectProvider()` is checked before anything
  renders, and the mic appears only where a provider actually exists (ADR-010, ADR-019). A
  button that apologises is still worse than no button.
- **Where the missing capability IS the feature, explain it.** `app/voice.tsx` says which
  reason applies and offers typing; `app/assistant.tsx` just omits the mic, because typing is
  already its primary affordance there. Silence is right when an equivalent path is visible,
  and wrong when the user came for the thing that is missing.
- Partner search deliberately has no offline fallback: stale fund-health data would route
  someone to a branch that cannot help them. Failing visibly is correct there.
