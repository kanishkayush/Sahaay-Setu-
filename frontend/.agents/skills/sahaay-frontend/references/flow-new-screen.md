# flow-new-screen

**A route is a file under `app/`. Screens hold layout and interaction only — no business
logic, no data access beyond a hook.**

## Why it matters

expo-router derives routes from the file tree, so a misplaced file is a broken or duplicated
route. Keeping logic out of screens is what makes the calculator and rule engine testable
without a renderer, and what keeps a screen readable at a glance.

## Wrong

```tsx
// app/loan.tsx — business logic inlined in the screen
export default function LoanScreen() {
  const r = rate / 12 / 100;
  const emi = (principal * r * (1 + r) ** n) / ((1 + r) ** n - 1); // ← belongs in features/
  return <View style={{ padding: 16, backgroundColor: '#fff' }}>…</View>; // ← raw values
}
```

## Right

```tsx
// app/(tabs)/calculator.tsx
import { useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { Screen, Text } from '@/components/ui';
import { calculateEmi } from '@/features/calculator/emi';

export default function CalculatorScreen() {
  const { t } = useTranslation();
  const result = useMemo(
    () => calculateEmi({ principal, annualRatePct: rate, tenureMonths: tenure }),
    [principal, rate, tenure],
  );

  return (
    <Screen>
      <Text variant="title">{t('calculator.title')}</Text>
      {/* … */}
    </Screen>
  );
}

const styles = StyleSheet.create({/* values from @/theme only */});
```

## Steps

1. Create the file under `app/`. Path is the route: `app/scheme/[id].tsx` → `/scheme/123`.
2. Register it in `app/_layout.tsx` if it needs specific header options.
3. Wrap the body in `<Screen>` for safe-area, background and scroll handling.
4. Every string via `t()`; every colour and spacing from `@/theme`.
5. `StyleSheet.create` at the bottom of the file.

## Notes

- Group routes with parentheses — `app/(tabs)/` is a layout group and does not appear in URLs.
- Deep-linkable params are how the assistant and scheme pages hand off to the calculator, e.g.
  `/(tabs)/calculator?principal=200000&rate=6.5`. Read them with `useLocalSearchParams`.
- After adding a route, run `npx expo export --platform android`. A typechecking screen can
  still break the module graph.
