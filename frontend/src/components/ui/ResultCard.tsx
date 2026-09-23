import { StyleSheet, View } from 'react-native';
import { Text } from './Text';
import { colors, radius, spacing } from '@/theme';

/**
 * The high-contrast result card from the Open Design iOS calculator: one figure
 * the user came for, at the largest size on the screen, with supporting numbers
 * below a rule.
 *
 * The EMI is what someone plans their life around, so it gets the whole card.
 */
export type ResultCardProps = {
  eyebrow: string;
  value: string;
  caption?: string;
  footer?: { value: string; label: string }[];
};

export function ResultCard({ eyebrow, value, caption, footer = [] }: ResultCardProps) {
  return (
    <View style={styles.card}>
      <Text variant="label" color={colors.textOnInverse} style={styles.eyebrow}>
        {eyebrow}
      </Text>
      <Text variant="hero" color={colors.textInverse} numberOfLines={1} adjustsFontSizeToFit>
        {value}
      </Text>
      {caption ? (
        <Text variant="caption" color={colors.textOnInverse}>
          {caption}
        </Text>
      ) : null}

      {footer.length > 0 ? (
        <View style={styles.footer}>
          {footer.map((item) => (
            <View key={item.label} style={styles.footerItem}>
              <Text
                variant="statValue"
                color={colors.textInverse}
                numberOfLines={1}
                adjustsFontSizeToFit
              >
                {item.value}
              </Text>
              <Text variant="caption" color={colors.textOnInverse}>
                {item.label}
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
    backgroundColor: colors.inverse,
    borderRadius: radius.lg,
    padding: spacing.xxl,
    gap: spacing.xs,
  },
  eyebrow: { textTransform: 'uppercase' },
  footer: {
    flexDirection: 'row',
    gap: spacing.lg,
    marginTop: spacing.lg,
    paddingTop: spacing.lg,
    borderTopWidth: 1,
    borderTopColor: colors.inverseAlt,
  },
  footerItem: { flex: 1, gap: 2 },
});
