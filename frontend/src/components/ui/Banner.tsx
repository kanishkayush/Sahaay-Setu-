import { StyleSheet, View } from 'react-native';
import { Icon, type IconName } from './Icon';
import { Text } from './Text';
import { radius, spacing, useTheme, type ColorTokens } from '@/theme';

type Tone = 'info' | 'warning' | 'danger' | 'success';

function tones(colors: ColorTokens): Record<Tone, { bg: string; fg: string; icon: IconName }> {
  return {
    info: { bg: colors.infoSurface, fg: colors.infoText, icon: 'info' },
    warning: { bg: colors.warningSurface, fg: colors.warningText, icon: 'alert' },
    danger: { bg: colors.dangerSurface, fg: colors.dangerText, icon: 'alert' },
    success: { bg: colors.successSurface, fg: colors.successText, icon: 'check' },
  };
}

export type BannerProps = {
  tone?: Tone;
  title?: string;
  message: string;
};

export function Banner({ tone = 'info', title, message }: BannerProps) {
  const { colors } = useTheme();
  const t = tones(colors)[tone];
  return (
    <View accessibilityRole="alert" style={[styles.banner, { backgroundColor: t.bg }]}>
      <Icon name={t.icon} size={20} color={t.fg} strokeWidth={2} />
      <View style={styles.body}>
        {title ? (
          <Text variant="bodyStrong" color={t.fg}>
            {title}
          </Text>
        ) : null}
        <Text variant="caption" color={colors.textSecondary}>
          {message}
        </Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  banner: {
    flexDirection: 'row',
    gap: spacing.md,
    padding: spacing.lg,
    borderRadius: radius.md,
  },
  body: { flex: 1, gap: 2 },
});
