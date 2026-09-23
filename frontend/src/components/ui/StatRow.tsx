import { StyleSheet, View } from 'react-native';
import { Text } from './Text';
import { colors, spacing } from '@/theme';

/**
 * Three figures side by side, value above label — the pattern the Open Design
 * system uses on every scheme card ("₹2.25 L / you could get").
 *
 * The value is large and the label small and muted, so the number is what the
 * eye lands on. Values are pre-formatted strings: formatting money is the
 * caller's job, via @/utils/format, so grouping stays Indian everywhere.
 *
 * Pass a value that already fits — use formatStatCurrency ("₹1.3L"), not
 * formatCompactCurrency ("₹1.26 lakh"). adjustsFontSizeToFit shrinks the text on
 * native but is a no-op on react-native-web, where an oversized value truncates
 * to "₹1.26 …" instead.
 */

export type Stat = {
  value: string;
  label: string;
  /** Rendered small and raised next to the value, e.g. the % in "6%". */
  suffix?: string;
};

export function StatRow({ stats, bordered = true }: { stats: Stat[]; bordered?: boolean }) {
  return (
    <View style={[styles.row, bordered && styles.bordered]}>
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
  bordered: {
    borderTopWidth: 1,
    borderBottomWidth: 1,
    borderColor: colors.borderSoft,
    marginVertical: spacing.md,
  },
  stat: { flex: 1, gap: 2 },
  valueLine: { flexDirection: 'row', alignItems: 'baseline', gap: 2 },
  suffix: { marginBottom: 4 },
});
