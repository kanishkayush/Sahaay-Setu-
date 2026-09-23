# a11y-touch-and-contrast

**48dp minimum touch targets. 16px minimum body text. WCAG AA contrast. Status never signalled
by colour alone.**

## Why it matters

Our users are frequently older, frequently first-time smartphone owners, frequently outdoors in
direct sun, on cheap panels with poor contrast ratios. A 32dp button that works fine on a
developer's flagship in an office is genuinely unusable in a village market at midday.

Colour-only status fails twice over: for the ~8% of men with colour vision deficiency, and for
everyone in glare.

## Wrong

```tsx
<Pressable style={{ height: 32, padding: 4 }} onPress={apply}>
  <Text style={{ fontSize: 12 }}>Apply</Text>
</Pressable>

// status by colour alone
<View style={{ width: 8, height: 8, backgroundColor: red }} />
```

## Right

```tsx
import { Button, Chip } from '@/components/ui';
import { MIN_TOUCH_SIZE } from '@/theme';

<Button title={t('schemes.openCalculator')} onPress={apply} />   // min 48dp built in

// status carries an icon AND a label — colour is the third signal, not the only one
<Chip
  label={t('partners.status.NOT_ACCEPTING')}
  tone="danger"
  prefix="✕"
/>
```

Custom pressables:

```tsx
<Pressable
  accessibilityRole="button"
  accessibilityLabel={t('partners.call')}
  style={{ minHeight: MIN_TOUCH_SIZE, minWidth: MIN_TOUCH_SIZE }}
  onPress={call}
/>
```

## The floor

|               | Value                   | Never below                             |
| ------------- | ----------------------- | --------------------------------------- |
| Touch target  | 48dp (`MIN_TOUCH_SIZE`) | 48dp                                    |
| Body text     | 16px (`variant="body"`) | 13px (`variant="label"`)                |
| Text contrast | WCAG AA, 4.5:1          | 4.5:1                                   |
| Font scaling  | respected to 1.6×       | must not be disabled on meaningful text |

## Status signalling

Every status in the app uses the same three-signal pattern:

```tsx
const STATUS_TONE = { ACCEPTING: 'success', LIMITED: 'warning', NOT_ACCEPTING: 'danger' };
const STATUS_PREFIX = { ACCEPTING: '✓', LIMITED: '!', NOT_ACCEPTING: '✕' };
```

Icon + translated label + colour. Remove any one and it still reads.

## Notes

- `accessibilityRole` and `accessibilityLabel` on everything interactive. `accessibilityState`
  for selected/disabled/busy.
- `Banner` carries `accessibilityRole="alert"` so screen readers announce it.
- Prefer big explicit controls over compact clever ones — see `a11y-inputs.md`.
