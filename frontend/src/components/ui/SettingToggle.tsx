import { Pressable, StyleSheet, Switch, View } from 'react-native';
import { Text } from './Text';
import { radius, spacing, MIN_TOUCH_SIZE, useTheme } from '@/theme';

export type SettingToggleProps = {
  title: string;
  subtitle: string;
  value: boolean;
  onChange: (value: boolean) => void;
};

export function SettingToggle({ title, subtitle, value, onChange }: SettingToggleProps) {
  const { colors } = useTheme();
  return (
    <Pressable
      accessibilityRole="switch"
      accessibilityState={{ checked: value }}
      accessibilityLabel={`${title}. ${subtitle}`}
      onPress={() => onChange(!value)}
      style={[
        styles.row,
        {
          backgroundColor: colors.surface,
          borderColor: colors.borderSoft,
        },
      ]}
    >
      <View style={styles.body}>
        <Text variant="bodyStrong">{title}</Text>
        <Text variant="caption" color={colors.textMuted}>
          {subtitle}
        </Text>
      </View>
      <View pointerEvents="none">
        <Switch
          value={value}
          trackColor={{ false: colors.border, true: colors.primary }}
          thumbColor={value ? colors.controlSelectedText : colors.surface}
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
    borderRadius: radius.lg,
    borderWidth: 1,
  },
  body: { flex: 1, gap: 2 },
});
