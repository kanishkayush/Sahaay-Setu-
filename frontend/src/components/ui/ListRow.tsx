import { Pressable, StyleSheet, View } from 'react-native';
import { Icon, type IconName } from './Icon';
import { Text } from './Text';
import { radius, spacing, MIN_TOUCH_SIZE, useTheme } from '@/theme';

export type ListRowProps = {
  icon: IconName;
  title: string;
  subtitle?: string;
  onPress: () => void;
  last?: boolean;
  tone?: 'default' | 'accent';
};

export function ListRow({ icon, title, subtitle, onPress, last, tone = 'default' }: ListRowProps) {
  const { colors } = useTheme();
  const accent = tone === 'accent';
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={subtitle ? `${title}. ${subtitle}` : title}
      onPress={onPress}
      style={({ pressed }) => [
        styles.row,
        !last && { borderBottomWidth: 1, borderBottomColor: colors.borderSoft },
        pressed && { backgroundColor: colors.surfaceAlt },
      ]}
    >
      <View
        style={[
          styles.iconWrap,
          { backgroundColor: accent ? colors.primarySurface : colors.background },
        ]}
      >
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

export function ListGroup({ children }: { children: React.ReactNode }) {
  const { colors } = useTheme();
  return (
    <View
      style={[
        styles.group,
        { backgroundColor: colors.surface, borderColor: colors.borderSoft },
      ]}
    >
      {children}
    </View>
  );
}

const styles = StyleSheet.create({
  group: {
    borderRadius: radius.lg,
    borderWidth: 1,
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
  iconWrap: {
    width: 44,
    height: 44,
    borderRadius: radius.pill,
    alignItems: 'center',
    justifyContent: 'center',
  },
  body: { flex: 1, gap: 2 },
});
