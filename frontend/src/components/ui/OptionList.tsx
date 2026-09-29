import { Pressable, StyleSheet, View } from 'react-native';
import { Icon } from './Icon';
import { Text } from './Text';
import { radius, spacing, MIN_TOUCH_SIZE, useTheme } from '@/theme';

export type Option<T extends string> = {
  value: T;
  label: string;
  description?: string;
};

export type OptionListProps<T extends string> = {
  options: Option<T>[];
  value: T | undefined;
  onChange: (value: T) => void;
};

export function OptionList<T extends string>({ options, value, onChange }: OptionListProps<T>) {
  const { colors } = useTheme();
  return (
    <View style={[styles.group, { backgroundColor: colors.surface, borderColor: colors.border }]}>
      {options.map((option, index) => {
        const selected = option.value === value;
        return (
          <Pressable
            key={option.value}
            accessibilityRole="radio"
            accessibilityState={{ selected }}
            accessibilityLabel={
              option.description ? `${option.label}. ${option.description}` : option.label
            }
            onPress={() => onChange(option.value)}
            style={({ pressed }) => [
              styles.option,
              index < options.length - 1 && { borderBottomWidth: 1, borderBottomColor: colors.border },
              selected && { backgroundColor: colors.primarySurface },
              pressed && { backgroundColor: colors.surfaceAlt },
            ]}
          >
            <View style={styles.body}>
              <Text variant="body" color={selected ? colors.text : colors.textSecondary}>
                {option.label}
              </Text>
              {option.description ? (
                <Text variant="caption" color={colors.textMuted}>
                  {option.description}
                </Text>
              ) : null}
            </View>

            {selected ? (
              <Icon name="check" size={21} color={colors.primary} strokeWidth={2.2} />
            ) : null}
          </Pressable>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  group: {
    borderRadius: radius.lg,
    borderWidth: 1,
    overflow: 'hidden',
  },
  option: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.md,
    minHeight: MIN_TOUCH_SIZE + 12,
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.md,
  },
  body: { flex: 1, gap: 2 },
});
