import { Pressable, StyleSheet, View } from 'react-native';
import { Text } from './Text';
import { radius, shadow, spacing, MIN_TOUCH_SIZE, useTheme } from '@/theme';

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
  const { colors } = useTheme();
  return (
    <View
      style={[
        styles.track,
        { backgroundColor: colors.glass, borderColor: colors.glassBorder },
      ]}
    >
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
              active && {
                backgroundColor: colors.segmentSelectedBackground,
                ...shadow.card,
              },
              pressed && styles.pressed,
            ]}
          >
            <Text variant="bodyStrong" color={active ? colors.segmentSelectedText : colors.textMuted}>
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
    borderRadius: radius.md,
    borderWidth: 1,
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
  pressed: { opacity: 0.7 },
});
