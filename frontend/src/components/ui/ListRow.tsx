import { Pressable, StyleSheet, View } from 'react-native';
import { Icon, type IconName } from './Icon';
import { Text } from './Text';
import { colors, radius, spacing, MIN_TOUCH_SIZE } from '@/theme';

/**
 * Grouped list row — icon, title, optional subtitle, chevron.
 *
 * Replaces the square tile grid from v0. The Open Design system moved to this
 * because a row gives each action a one-line explanation, which matters far more
 * than compactness for a user who does not already know what "Channel Partner"
 * means.
 */

export type ListRowProps = {
  icon: IconName;
  title: string;
  subtitle?: string;
  onPress: () => void;
  /** Renders without the bottom divider — set on the last row of a group. */
  last?: boolean;
  tone?: 'default' | 'accent';
};

export function ListRow({ icon, title, subtitle, onPress, last, tone = 'default' }: ListRowProps) {
  const accent = tone === 'accent';
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={subtitle ? `${title}. ${subtitle}` : title}
      onPress={onPress}
      style={({ pressed }) => [styles.row, !last && styles.divider, pressed && styles.pressed]}
    >
      <View style={[styles.iconWrap, accent && styles.iconWrapAccent]}>
        <Icon name={icon} size={22} color={accent ? colors.primary : colors.textSecondary} />
      </View>

      <View style={styles.body}>
        <Text variant="bodyStrong">{title}</Text>
        {subtitle ? (
          <Text variant="caption" color={colors.textMuted}>
            {subtitle}
          </Text>
        ) : null}
      </View>

      <Icon name="right" size={20} color={colors.textMuted} />
    </Pressable>
  );
}

/** Wraps rows in the card that groups them. */
export function ListGroup({ children }: { children: React.ReactNode }) {
  return <View style={styles.group}>{children}</View>;
}

const styles = StyleSheet.create({
  group: {
    backgroundColor: colors.surface,
    borderRadius: radius.lg,
    borderWidth: 1,
    borderColor: colors.borderSoft,
    overflow: 'hidden',
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.lg,
    minHeight: MIN_TOUCH_SIZE + 24,
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.lg,
  },
  divider: { borderBottomWidth: 1, borderBottomColor: colors.borderSoft },
  pressed: { backgroundColor: colors.surfaceAlt },
  iconWrap: {
    width: 44,
    height: 44,
    borderRadius: radius.pill,
    backgroundColor: colors.background,
    alignItems: 'center',
    justifyContent: 'center',
  },
  iconWrapAccent: { backgroundColor: colors.primarySurface },
  body: { flex: 1, gap: 2 },
});
