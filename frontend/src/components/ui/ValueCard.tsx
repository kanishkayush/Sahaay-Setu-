import { StyleSheet, View } from 'react-native';
import { Text } from './Text';
import { radius, spacing, useTheme } from '@/theme';

export type ValueStat = { value: string; label: string };

export type ValueCardProps = {
  eyebrow: string;
  headline: string;
  stats?: ValueStat[];
};

export function ValueCard({ eyebrow, headline, stats = [] }: ValueCardProps) {
  const { colors } = useTheme();
  return (
    <View style={[styles.card, { backgroundColor: colors.inverse }]}>
      <Text variant="label" color={colors.textOnInverse} style={styles.eyebrow}>
        {eyebrow}
      </Text>
      <Text variant="display" color={colors.textInverse}>
        {headline}
      </Text>

      {stats.length > 0 ? (
        <View style={styles.stats}>
          {stats.map((stat) => (
            <View key={stat.label} style={styles.stat}>
              <Text
                variant="statValue"
                color={colors.textInverse}
                numberOfLines={1}
                adjustsFontSizeToFit
              >
                {stat.value}
              </Text>
              <Text variant="caption" color={colors.textOnInverse}>
                {stat.label}
              </Text>
            </View>
          ))}
        </View>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    borderRadius: radius.lg,
    padding: spacing.xxl,
    gap: spacing.md,
  },
  eyebrow: { textTransform: 'uppercase' },
  stats: { flexDirection: 'row', gap: spacing.lg, marginTop: spacing.sm },
  stat: { flex: 1, gap: 2 },
});
