import { Pressable, StyleSheet, View } from 'react-native';
import { Icon } from './Icon';
import { Text } from './Text';
import { colors, radius, spacing, MIN_TOUCH_SIZE } from '@/theme';

/**
 * Single-select list, grouped into one card — the pattern from the Open Design
 * iOS recommender sheet.
 *
 * Preferred over a native picker throughout the app: a picker hides its options
 * behind a tap, which is a real barrier for users new to smartphones. Every
 * option stays visible and readable.
 *
 * Selection is a checkmark on the chosen row ONLY. (The source mockup renders a
 * check on every row — a static artifact, not a spec; copying it would make the
 * selected state unreadable.)
 */
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
  return (
    <View style={styles.group}>
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
              index < options.length - 1 && styles.divider,
              selected && styles.selected,
              pressed && styles.pressed,
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

            {/* Checkmark on the selected row only — the non-colour signal. */}
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
    backgroundColor: colors.surface,
    borderRadius: radius.lg,
    borderWidth: 1,
    borderColor: colors.border,
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
  divider: { borderBottomWidth: 1, borderBottomColor: colors.border },
  selected: { backgroundColor: colors.primarySurface },
  pressed: { backgroundColor: colors.surfaceAlt },
  body: { flex: 1, gap: 2 },
});
