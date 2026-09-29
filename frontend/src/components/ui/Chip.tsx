import { Pressable, StyleSheet, View } from 'react-native';
import { Icon, type IconName } from './Icon';
import { Text } from './Text';
import { radius, spacing, useTheme, type ColorTokens } from '@/theme';

export type ChipTone = 'neutral' | 'primary' | 'success' | 'warning' | 'danger' | 'info';

function tones(colors: ColorTokens): Record<ChipTone, { bg: string; fg: string; border: string }> {
  return {
    neutral: { bg: colors.surface, fg: colors.textSecondary, border: colors.border },
    primary: { bg: colors.primarySurface, fg: colors.primary, border: colors.primarySurface },
    success: { bg: colors.successSurface, fg: colors.successText, border: colors.successSurface },
    warning: { bg: colors.warningSurface, fg: colors.warningText, border: colors.warningSurface },
    danger: { bg: colors.dangerSurface, fg: colors.dangerText, border: colors.dangerSurface },
    info: { bg: colors.infoSurface, fg: colors.infoText, border: colors.infoSurface },
  };
}

export type ChipProps = {
  label: string;
  tone?: ChipTone;
  icon?: IconName;
  selected?: boolean;
  onPress?: () => void;
};

export function Chip({ label, tone = 'neutral', icon, selected, onPress }: ChipProps) {
  const { colors } = useTheme();
  const t = tones(colors)[tone];
  const fg = selected ? colors.controlSelectedText : t.fg;

  const body = (
    <View
      style={[
        styles.chip,
        {
          backgroundColor: selected ? colors.controlSelectedBackground : t.bg,
          borderColor: selected ? colors.controlSelectedBorder : t.border,
        },
      ]}
    >
      {icon ? (
        <Icon
          name={icon}
          size={15}
          color={selected ? colors.controlSelectedIcon : fg}
          strokeWidth={2}
        />
      ) : null}
      <Text variant="label" color={fg}>
        {label}
      </Text>
    </View>
  );

  if (!onPress) return body;
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityState={{ selected: Boolean(selected) }}
      accessibilityLabel={label}
      onPress={onPress}
      style={({ pressed }) => pressed && styles.pressed}
    >
      {body}
    </Pressable>
  );
}

const styles = StyleSheet.create({
  chip: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.xs + 2,
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.md - 2,
    borderRadius: radius.pill,
    borderWidth: 1,
  },
  pressed: { opacity: 0.75 },
});
