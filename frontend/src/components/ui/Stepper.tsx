import { Pressable, StyleSheet, View } from 'react-native';
import { Text } from './Text';
import { radius, spacing, MIN_TOUCH_SIZE, useTheme } from '@/theme';

export type StepperProps = {
  label: string;
  hint?: string;
  value: number;
  min: number;
  max: number;
  step: number;
  suffix?: string;
  format?: (value: number) => string;
  onChange: (value: number) => void;
  decreaseLabel: string;
  increaseLabel: string;
};

export function Stepper({
  label,
  hint,
  value,
  min,
  max,
  step,
  suffix,
  format,
  onChange,
  decreaseLabel,
  increaseLabel,
}: StepperProps) {
  const { colors } = useTheme();
  const clamp = (n: number) => Math.min(max, Math.max(min, n));
  const display = format ? format(value) : String(value);
  const progress = max === min ? 0 : (value - min) / (max - min);

  return (
    <View style={styles.wrapper}>
      <Text variant="subheading">{label}</Text>
      {hint ? (
        <Text variant="caption" color={colors.textMuted}>
          {hint}
        </Text>
      ) : null}

      <View style={styles.row}>
        <Pressable
          accessibilityRole="button"
          accessibilityLabel={decreaseLabel}
          disabled={value <= min}
          onPress={() => onChange(clamp(value - step))}
          style={({ pressed }) => [
            styles.stepBtn,
            {
              backgroundColor: colors.primarySurface,
              borderColor: colors.primary,
            },
            value <= min && styles.stepDisabled,
            pressed && styles.pressed,
          ]}
        >
          <Text variant="title" color={colors.primary}>
            −
          </Text>
        </Pressable>

        <View
          style={[
            styles.valueBox,
            { backgroundColor: colors.inputBackground, borderColor: colors.border },
          ]}
        >
          <Text variant="title" color={colors.primary} center>
            {display}
            {suffix ? (
              <Text variant="body" color={colors.textSecondary}>
                {' '}
                {suffix}
              </Text>
            ) : null}
          </Text>
        </View>

        <Pressable
          accessibilityRole="button"
          accessibilityLabel={increaseLabel}
          disabled={value >= max}
          onPress={() => onChange(clamp(value + step))}
          style={({ pressed }) => [
            styles.stepBtn,
            {
              backgroundColor: colors.primarySurface,
              borderColor: colors.primary,
            },
            value >= max && styles.stepDisabled,
            pressed && styles.pressed,
          ]}
        >
          <Text variant="title" color={colors.primary}>
            +
          </Text>
        </Pressable>
      </View>

      <View style={[styles.track, { backgroundColor: colors.surfaceAlt }]}>
        <View style={[styles.fill, { width: `${Math.round(progress * 100)}%`, backgroundColor: colors.primary }]} />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  wrapper: { gap: spacing.sm },
  row: { flexDirection: 'row', alignItems: 'center', gap: spacing.md },
  stepBtn: {
    width: MIN_TOUCH_SIZE + 8,
    height: MIN_TOUCH_SIZE + 8,
    borderRadius: radius.md,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1.5,
  },
  stepDisabled: { opacity: 0.35 },
  pressed: { opacity: 0.8 },
  valueBox: {
    flex: 1,
    minHeight: MIN_TOUCH_SIZE + 8,
    justifyContent: 'center',
    borderWidth: 1.5,
    borderRadius: radius.md,
    paddingHorizontal: spacing.md,
  },
  track: { height: 6, borderRadius: 3, overflow: 'hidden' },
  fill: { height: 6, borderRadius: 3 },
});
