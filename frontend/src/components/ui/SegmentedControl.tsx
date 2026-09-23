import { Pressable, StyleSheet, View } from 'react-native';
import { Text } from './Text';
import { colors, radius, shadow, spacing, MIN_TOUCH_SIZE } from '@/theme';

/**
 * Premium glassmorphism segmented control.
 */
export type Segment<T extends string> = { value: T; label: string };

export type SegmentedControlProps<T extends string> = {
  segments: Segment<T>[];
  value: T;
  onChange: (value: T) => void;
};

export function SegmentedControl<T extends string>({
  segments,
  value,
  onChange,
}: SegmentedControlProps<T>) {
  return (
    <View style={styles.track}>
      {segments.map((segment) => {
        const active = segment.value === value;
        return (
          <Pressable
            key={segment.value}
            accessibilityRole="tab"
            accessibilityState={{ selected: active }}
            accessibilityLabel={segment.label}
            onPress={() => onChange(segment.value)}
            style={({ pressed }) => [
              styles.segment,
              active && styles.segmentActive,
              pressed && styles.pressed,
            ]}
          >
            <Text variant="bodyStrong" color={active ? colors.text : colors.textMuted}>
              {segment.label}
            </Text>
          </Pressable>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  track: {
    flexDirection: 'row',
    backgroundColor: colors.glass,
    borderRadius: radius.md,
    borderWidth: 1,
    borderColor: colors.glassBorder,
    padding: 4,
    gap: 4,
    ...shadow.glass,
  },
  segment: {
    flex: 1,
    minHeight: MIN_TOUCH_SIZE - 8,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: radius.sm + 2,
    paddingHorizontal: spacing.md,
  },
  segmentActive: {
    backgroundColor: colors.surface,
    ...shadow.card,
  },
  pressed: { opacity: 0.7 },
});
