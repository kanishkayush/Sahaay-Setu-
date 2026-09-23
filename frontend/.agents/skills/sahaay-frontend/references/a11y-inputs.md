# a11y-inputs

**Prefer large, always-visible controls over compact ones that hide state behind a gesture.
Steppers over sliders; option lists over pickers.**

## Why it matters

Two failure modes we designed around:

**Dragging is hard.** A thin slider handle demands fine motor control on a small, cheap,
sometimes-cracked touchscreen. It is worse with age, worse with a tremor, and effectively
impossible with a screen reader.

**Pickers hide the options.** A native picker shows one value and requires a tap to discover
the rest. For a user who is not fluent in "there is a menu behind this", the other options
simply do not exist.

## Wrong

```tsx
import Slider from '@react-native-community/slider';

<Slider minimumValue={6} maximumValue={120} step={6} value={tenure} onValueChange={setTenure} />;
// unlabelled, undraggable for many users, invisible to a screen reader
```

```tsx
<Picker selectedValue={projectType} onValueChange={setProjectType}>
  {PROJECT_TYPES.map((p) => (
    <Picker.Item key={p} label={p} value={p} />
  ))}
</Picker>
```

## Right

```tsx
import { OptionList, Stepper } from '@/components/ui';

<Stepper
  label={t('calculator.tenure')}
  value={tenure} min={6} max={120} step={6}
  format={(v) => formatMonths(v, monthWord, yearWord)}
  onChange={setTenure}
  decreaseLabel={t('a11y.decrease')}
  increaseLabel={t('a11y.increase')}
/>

<OptionList
  options={PROJECT_TYPES.map((p) => ({
    value: p.value,
    label: t(`projectType.${p.value}`),
    emoji: p.emoji,
  }))}
  value={projectType}
  onChange={setProjectType}
/>
```

Two 56dp buttons and a readable value beat a drag handle. Every option visible beats a menu.

## Numeric and money input

`AmountInput` echoes the value back in words-ish form and offers preset chips:

```tsx
<AmountInput
  label={t('recommender.projectCostQuestion')}
  hint={t('recommender.projectCostHint')}
  value={projectCost}
  onChange={setProjectCost}
  presets={[50_000, 140_000, 500_000, 2_000_000]}
/>
```

The echo is not decoration. An order-of-magnitude typo — ₹20,000 entered as ₹2,00,000 —
changes which scheme someone is matched to. Showing "₹2 lakh" under the field makes that
mistake visible to someone who finds long digit strings hard to parse. The presets let a user
avoid the keypad entirely.

## One question per screen

The recommender wizard asks five questions across five screens rather than one long form.
Completion rates for long forms among first-time smartphone users are poor, and one question
per screen leaves room for large targets and a plain-language prompt.

## Notes

- ADR-007 records the stepper decision.
- `keyboardType="number-pad"` plus `inputMode="numeric"` for amounts — the plain numeric keypad
  has larger keys than the full keyboard.
- Every control needs `accessibilityRole` (`radio` for `OptionList`, `button` for `Stepper`)
  and an `accessibilityLabel`.
