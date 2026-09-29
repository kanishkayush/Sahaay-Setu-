import { StyleSheet, View } from 'react-native';
import { Text } from './Text';
import { radius, spacing, useTheme } from '@/theme';

export type ResultCardProps = {
  eyebrow: string;
  value: string;
  caption?: string;
  footer?: { value: string; label: string }[];
};

export function ResultCard({ eyebrow, value, caption, footer = [] }: ResultCardProps) {
  const { colors } = useTheme();
  return (
    <View style={[styles.card, { backgroundColor: colors.inverse }]}>
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
        <View style={[styles.footer, { borderTopColor: colors.inverseAlt }]}>
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
  },
  footerItem: { flex: 1, gap: 2 },
});
