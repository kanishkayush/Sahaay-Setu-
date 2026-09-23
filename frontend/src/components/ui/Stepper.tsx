import { Pressable, StyleSheet, View } from 'react-native';
import { Text } from './Text';
import { colors, radius, spacing, MIN_TOUCH_SIZE } from '@/theme';

export type StepperProps = {
  label: string;
  hint?: string;
  value: number;
  min: number;
  max: number;
  step: number;
  /** Rendered next to the value, e.g. "months" or "%". */
  suffix?: string;
  format?: (value: number) => string;
  onChange: (value: number) => void;
  decreaseLabel: string;
  increaseLabel: string;
};

/**
 * A −/+ stepper rather than a drag slider.
 *
 * Deliberate: dragging a thin slider handle precisely is hard on a small, cheap
 * touchscreen, and impossible for users with limited dexterity. Two large
 * buttons are unambiguous and fully accessible to screen readers.
 */
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
            value <= min && styles.stepDisabled,
            pressed && styles.pressed,
          ]}
        >
          <Text variant="title" color={colors.primary}>
            −
          </Text>
        </Pressable>

        <View style={styles.valueBox}>
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
            value >= max && styles.stepDisabled,
            pressed && styles.pressed,
          ]}
        >
          <Text variant="title" color={colors.primary}>
            +
          </Text>
        </Pressable>
      </View>

      <View style={styles.track}>
        <View style={[styles.fill, { width: `${Math.round(progress * 100)}%` }]} />
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
    backgroundColor: colors.primarySurface,
    borderWidth: 1.5,
    borderColor: colors.primary,
  },
  stepDisabled: { opacity: 0.35 },
  pressed: { opacity: 0.8 },
  valueBox: {
    flex: 1,
    minHeight: MIN_TOUCH_SIZE + 8,
    justifyContent: 'center',
    backgroundColor: colors.surface,
    borderWidth: 1.5,
    borderColor: colors.border,
    borderRadius: radius.md,
    paddingHorizontal: spacing.md,
  },
  track: { height: 6, borderRadius: 3, backgroundColor: colors.surfaceAlt, overflow: 'hidden' },
  fill: { height: 6, borderRadius: 3, backgroundColor: colors.primary },
});
