import { StyleSheet, View } from 'react-native';
import { useTranslation } from 'react-i18next';

import type { LanguageCode, Scheme, SchemeRecommendation } from '@/api/contracts';
import { Card, Chip, StatRow, Text } from '@/components/ui';
import { pickLocalized } from '@/i18n/localized';
import { colors, spacing } from '@/theme';
import { formatMonths, formatPercent, formatStatCurrency } from '@/utils/format';

/**
 * Scheme card, per the Open Design system: a numbered rank badge, the code as an
 * eyebrow, and three figures — what you get, the rate, the term.
 *
 * The three-figure row is the point. Those are the numbers a beneficiary is
 * actually comparing between schemes, so they get the largest type on the card.
 */
export type SchemeCardProps = {
  scheme: Scheme;
  language: LanguageCode;
  onPress?: () => void;
  recommendation?: SchemeRecommendation;
  rank?: number;
};

export function SchemeCard({ scheme, language, onPress, recommendation, rank }: SchemeCardProps) {
  const { t } = useTranslation();
  const name = pickLocalized(scheme.name, language, scheme.code);
  const description = pickLocalized(scheme.shortDescription, language);

  const rate = recommendation?.applicableInterestRatePct ?? scheme.interestRateMinPct;
  const amount = recommendation?.eligibleLoanAmount ?? scheme.maxLoanAmount;
  const monthWord = t('common.months');
  const yearWord = t('common.years');

  return (
    <Card variant="glass" onPress={onPress} accessibilityLabel={name}>
      <View style={styles.header}>
        {rank !== undefined ? (
          <View style={styles.rank}>
            <Text variant="label" color={colors.textInverse}>
              {rank}
            </Text>
          </View>
        ) : null}

        <View style={styles.titleBlock}>
          <Text variant="heading" color={colors.text}>{name}</Text>
          <Text variant="label" color={colors.textMuted}>
            {scheme.code}
          </Text>
        </View>

        {recommendation ? (
          <Chip
            label={rank === 1 ? 'Recommended' : 'Potentially Eligible'}
            tone={rank === 1 ? 'success' : 'info'}
          />
        ) : null}
      </View>

      {description ? (
        <Text variant="caption" color={colors.textSecondary} style={styles.description}>
          {description}
        </Text>
      ) : null}

      <StatRow
        stats={[
          amount !== undefined && amount !== null ? {
            value: formatStatCurrency(amount),
            label: 'Maximum assistance',
          } : null,
          rate !== undefined && rate !== null ? { 
            value: formatPercent(rate), 
            label: 'Interest rate' 
          } : null,
          scheme.maxTenureMonths !== undefined && scheme.maxTenureMonths !== null ? {
            value: formatMonths(scheme.maxTenureMonths, monthWord, yearWord),
            label: 'Repayment period',
          } : null,
        ].filter(Boolean) as { value: string; label: string }[]}
      />

      <View style={styles.chips}>
        <Chip label={scheme.officialCategory.replace(/_/g, ' ')} tone="neutral" />
        {scheme.womenInterestRatePct !== undefined ? (
          <Chip
            label={t('schemes.womenRate', { rate: scheme.womenInterestRatePct })}
            tone="success"
            icon="check"
          />
        ) : null}
        {!scheme.verified ? (
          <Chip label={t('common.unverified')} tone="warning" icon="alert" />
        ) : null}
      </View>
    </Card>
  );
}

const styles = StyleSheet.create({
  header: { flexDirection: 'row', alignItems: 'flex-start', gap: spacing.md },
  rank: {
    width: 28,
    height: 28,
    borderRadius: 14,
    backgroundColor: colors.inverse,
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: 2,
  },
  titleBlock: { flex: 1, gap: 2 },
  description: { marginTop: spacing.sm },
  chips: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.sm },
});
