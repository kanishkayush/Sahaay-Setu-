import { Pressable, StyleSheet, View } from 'react-native';
import { Icon, type IconName } from './Icon';
import { Text } from './Text';
import { colors, radius, spacing } from '@/theme';

export type ChipTone = 'neutral' | 'primary' | 'success' | 'warning' | 'danger' | 'info';

/**
 * Pill chip, per the Open Design system: outlined when idle, solid dark when
 * selected — the filter row on the results screen.
 *
 * Status tones pair a low-saturation surface with an AA-passing text colour.
 * `icon` is how status stops depending on colour alone; keep passing it.
 */
const tones: Record<ChipTone, { bg: string; fg: string; border: string }> = {
  neutral: { bg: colors.surface, fg: colors.textSecondary, border: colors.border },
  primary: { bg: colors.primarySurface, fg: colors.primary, border: colors.primarySurface },
  success: { bg: colors.successSurface, fg: colors.successText, border: colors.successSurface },
  warning: { bg: colors.warningSurface, fg: colors.warningText, border: colors.warningSurface },
  danger: { bg: colors.dangerSurface, fg: colors.dangerText, border: colors.dangerSurface },
  info: { bg: colors.infoSurface, fg: colors.infoText, border: colors.infoSurface },
};

export type ChipProps = {
  label: string;
  tone?: ChipTone;
  /** The non-colour signal for status. Always pass it on a status chip. */
  icon?: IconName;
  selected?: boolean;
  onPress?: () => void;
};

export function Chip({ label, tone = 'neutral', icon, selected, onPress }: ChipProps) {
  const t = tones[tone];
  const fg = selected ? colors.textInverse : t.fg;

  const body = (
    <View
      style={[
        styles.chip,
        {
          backgroundColor: selected ? colors.inverse : t.bg,
          borderColor: selected ? colors.inverse : t.border,
        },
      ]}
    >
      {icon ? <Icon name={icon} size={15} color={fg} strokeWidth={2} /> : null}
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
