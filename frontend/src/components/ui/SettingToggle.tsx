import { Pressable, StyleSheet, Switch, View } from 'react-native';
import { Text } from './Text';
import { colors, radius, spacing, MIN_TOUCH_SIZE } from '@/theme';

/**
 * A switch with a title AND a sentence explaining what it does, from the Open
 * Design iOS partners screen.
 *
 * The explanation is the point. "Only those accepting" alone is a filter label;
 * "Hides partners with high NPAs or exhausted funds" teaches the routing rule
 * that is the whole reason requirement R3 exists. Never ship this without the
 * subtitle.
 */
export type SettingToggleProps = {
  title: string;
  subtitle: string;
  value: boolean;
  onChange: (value: boolean) => void;
};

export function SettingToggle({ title, subtitle, value, onChange }: SettingToggleProps) {
  return (
    <Pressable
      accessibilityRole="switch"
      accessibilityState={{ checked: value }}
      accessibilityLabel={`${title}. ${subtitle}`}
      onPress={() => onChange(!value)}
      style={styles.row}
    >
      <View style={styles.body}>
        <Text variant="bodyStrong">{title}</Text>
        <Text variant="caption" color={colors.textMuted}>
          {subtitle}
        </Text>
      </View>
      {/* Visual only. The row is the single accessible control, so the switch
          must not also be focusable — nested interactive elements are invalid
          HTML on web and read as two controls to a screen reader. */}
      <View pointerEvents="none">
        <Switch
          value={value}
          trackColor={{ false: colors.border, true: colors.primary }}
          thumbColor={colors.surface}
        />
      </View>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.lg,
    minHeight: MIN_TOUCH_SIZE + 16,
    padding: spacing.lg,
    backgroundColor: colors.surface,
    borderRadius: radius.lg,
    borderWidth: 1,
    borderColor: colors.borderSoft,
  },
  body: { flex: 1, gap: 2 },
});
