import { StyleSheet, View } from 'react-native';
import { Text } from './Text';
import { spacing, useTheme } from '@/theme';

export type Stat = {
  value: string;
  label: string;
  suffix?: string;
};

export function StatRow({ stats, bordered = true }: { stats: Stat[]; bordered?: boolean }) {
  const { colors } = useTheme();
  return (
    <View
      style={[
        styles.row,
        bordered && {
          borderTopWidth: 1,
          borderBottomWidth: 1,
          borderColor: colors.borderSoft,
          marginVertical: spacing.md,
        },
      ]}
    >
      {stats.map((stat) => (
        <View key={stat.label} style={styles.stat}>
          <View style={styles.valueLine}>
            <Text variant="statValue" numberOfLines={1} adjustsFontSizeToFit>
              {stat.value}
            </Text>
            {stat.suffix ? (
              <Text variant="label" color={colors.textMuted} style={styles.suffix}>
                {stat.suffix}
              </Text>
            ) : null}
          </View>
          <Text variant="caption" color={colors.textMuted}>
            {stat.label}
          </Text>
        </View>
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: 'row', gap: spacing.md, paddingVertical: spacing.lg },
  stat: { flex: 1, gap: 2 },
  valueLine: { flexDirection: 'row', alignItems: 'baseline', gap: 2 },
  suffix: { marginBottom: 4 },
});
