// @ts-nocheck
import { ActivityIndicator, Linking, StyleSheet, View } from 'react-native';
import { router, useLocalSearchParams } from 'expo-router';
import { useTranslation } from 'react-i18next';

import { Banner, Button, Card, Chip, Icon, Screen, Text } from '@/components/ui';
import { useScheme } from '@/hooks/useSchemes';
import { pickLocalized } from '@/i18n/localized';
import { useAppStore } from '@/store/useAppStore';
import { colors, spacing, useTheme } from '@/theme';
import { formatCompactCurrency, formatCurrency, formatMonths, formatPercent } from '@/utils/format';
import {
  isSchemeFinancialConfirmed,
  officialSourceUrl,
  schemeVerificationBadge,
  schemeVerificationKind,
} from '@/features/schemes/verification';

export default function SchemeDetailScreen() {
  const { colors } = useTheme();
  const { t } = useTranslation();
  const { id } = useLocalSearchParams<{ id: string }>();
  const language = useAppStore((s) => s.language);
  const savedIds = useAppStore((s) => s.savedSchemeIds);
  const toggleSaved = useAppStore((s) => s.toggleSavedScheme);

  const { data: scheme, isLoading, isError } = useScheme(id);

  if (isLoading) {
    return (
      <Screen>
        <ActivityIndicator
          size="large"
          color={colors.primary}
          style={styles.loader}
          accessibilityLabel={t('a11y.loading')}
        />
      </Screen>
    );
  }

  if (isError || !scheme) {
    return (
      <Screen>
        <Banner tone="danger" message={t('errors.notFound')} />
      </Screen>
    );
  }

  const name = pickLocalized(scheme.name, language, scheme.code);
  const isSaved = savedIds.includes(scheme.id);
  const monthWord = t('common.months');
  const yearWord = t('common.years');
  const verificationKind = schemeVerificationKind(scheme);
  const financialsConfirmed = isSchemeFinancialConfirmed(scheme);
  const notVerified = t('common.notVerified');
  const sourceUrl = officialSourceUrl(scheme);
  const verificationMessage =
    verificationKind === 'VERIFIED'
      ? null
      : verificationKind === 'PARTIAL'
        ? t('schemes.partialNotice')
        : t('schemes.unverifiedNotice');

  return (
    <Screen>
      <View style={styles.header}>
        <Text variant="title">{name}</Text>
        {scheme.implementingOrganization || scheme.sourceName ? (
          <Text variant="body" color={colors.textSecondary}>
            {scheme.implementingOrganization || scheme.sourceName}
          </Text>
        ) : null}
        <Text variant="body" color={colors.textSecondary}>
          {pickLocalized(scheme.shortDescription, language)}
        </Text>
        <View style={styles.chips}>
          <Chip label={t(`category.${scheme.officialCategory}`)} tone="primary" />
          <Chip label={scheme.code} tone="neutral" />
          {verificationKind === 'VERIFIED' ? (
            <Chip label={t('schemes.verifiedBadge')} tone="success" icon="check" />
          ) : (
            <Chip
              label={schemeVerificationBadge(verificationKind)}
              tone="warning"
              icon="info"
            />
          )}
        </View>
      </View>

      {verificationMessage ? (
        <Card>
          <Text variant="label">{t('schemes.verificationStatus')}</Text>
          <Text variant="body" color={colors.textSecondary} style={{ marginTop: spacing.sm }}>
            {verificationMessage}
          </Text>
          {sourceUrl ? (
            <View style={{ marginTop: spacing.md }}>
              <Text variant="label">{t('schemes.source')}</Text>
              <Button
                title={t('schemes.viewOfficialSource')}
                variant="outline"
                size="sm"
                onPress={() => Linking.openURL(sourceUrl).catch(() => {})}
              />
            </View>
          ) : null}
        </Card>
      ) : null}

      <Card>
        <Row
          label={t('schemes.loanRange')}
          value={
            financialsConfirmed
              ? scheme.minLoanAmount == null && scheme.maxLoanAmount == null
                ? t('common.notSpecified', 'Not specified')
                : `${scheme.minLoanAmount != null ? formatCompactCurrency(scheme.minLoanAmount) : '0'} – ${scheme.maxLoanAmount != null ? formatCompactCurrency(scheme.maxLoanAmount) : t('common.noLimit', 'No limit')}`
              : notVerified
          }
        />
        <Row
          label={t('schemes.interestRate')}
          value={
            financialsConfirmed && (scheme.interestRateMinPct != null || scheme.interestRateMaxPct != null)
              ? `${formatPercent(scheme.interestRateMinPct ?? scheme.interestRateMaxPct)} – ${formatPercent(scheme.interestRateMaxPct ?? scheme.interestRateMinPct)}`
              : notVerified
          }
        />
        {financialsConfirmed && scheme.womenInterestRatePct !== undefined ? (
          <Row
            label={t('schemes.womenRate', { rate: scheme.womenInterestRatePct })}
            value={formatPercent(scheme.womenInterestRatePct)}
            highlight
          />
        ) : null}
        <Row
          label={t('schemes.tenure')}
          value={
            financialsConfirmed && scheme.maxTenureMonths
              ? formatMonths(scheme.maxTenureMonths, monthWord, yearWord)
              : notVerified
          }
        />
        <Row
          label={t('schemes.moratorium')}
          value={
            financialsConfirmed && (scheme.moratoriumMinMonths != null || scheme.moratoriumMaxMonths != null)
              ? t('schemes.moratoriumRange', {
                  min: scheme.moratoriumMinMonths,
                  max: scheme.moratoriumMaxMonths,
                })
              : notVerified
          }
        />
        <Row
          label={t('schemes.incomeCeiling')}
          value={
            financialsConfirmed && scheme.maxAnnualFamilyIncome != null
              ? formatCurrency(scheme.maxAnnualFamilyIncome)
              : notVerified
          }
        />
        <Row
          label={t('schemes.fundingShare', {
            pct: financialsConfirmed ? Math.round((scheme.fundingSharePct ?? 0) * 100) : '—',
          })}
          value={
            financialsConfirmed && scheme.fundingSharePct != null
              ? `${Math.round(scheme.fundingSharePct * 100)}%`
              : notVerified
          }
          last
        />
      </Card>

      {scheme.eligibilityRules.length > 0 ? (
        <View style={styles.section}>
          <Text variant="subheading">{t('schemes.eligibility')}</Text>
          <Card>
            {scheme.eligibilityRules.map((rule, index) => (
              <View
                key={`${rule.field}-${index}`}
                style={[
                  styles.bullet,
                  index < scheme.eligibilityRules.length - 1 && styles.bulletBorder,
                ]}
              >
                <Icon name="check" size={18} color={colors.successText} strokeWidth={2.2} />
                <Text variant="body" style={styles.bulletText}>
                  {pickLocalized(rule.label, language)}
                </Text>
              </View>
            ))}
          </Card>
        </View>
      ) : null}

      {scheme.documentsRequired.length > 0 ? (
        <View style={styles.section}>
          <Text variant="subheading">{t('schemes.documents')}</Text>
          <Card>
            {scheme.documentsRequired.map((doc, index) => (
              <View
                key={index}
                style={[
                  styles.bullet,
                  index < scheme.documentsRequired.length - 1 && styles.bulletBorder,
                ]}
              >
                <Icon name="doc" size={18} color={colors.textMuted} />
                <Text variant="body" style={styles.bulletText}>
                  {pickLocalized(doc, language)}
                </Text>
              </View>
            ))}
          </Card>
        </View>
      ) : null}

      <View style={styles.section}>
        <Text variant="subheading">{t('schemes.whereToApply')}</Text>
        <Text variant="caption" color={colors.textSecondary}>
          {t('schemes.partnerTypes')}
        </Text>
        <View style={styles.chips}>
          {scheme.channelPartnerTypes.map((type) => (
            <Chip key={type} label={t(`partners.type.${type}`)} tone="info" />
          ))}
        </View>
      </View>

      <View style={styles.actions}>
        {financialsConfirmed ? (
          <Button
            title={t('schemes.openCalculator')}
            onPress={() =>
              router.push({
                pathname: '/(tabs)/calculator',
                params: {
                  principal: scheme.maxLoanAmount,
                  rate: scheme.interestRateMinPct,
                  tenure: scheme.maxTenureMonths,
                  moratorium: scheme.moratoriumMinMonths,
                  scheme: name,
                },
              })
            }
          />
        ) : null}
        <Button
          title={t('schemes.findPartners')}
          variant="outline"
          onPress={() => router.push('/(tabs)/partners')}
        />
        <Button
          title={isSaved ? t('schemes.saved') : t('schemes.save')}
          variant="ghost"
          size="sm"
          icon={
            <Icon
              name="check"
              size={18}
              color={isSaved ? colors.successText : colors.primary}
              strokeWidth={2.2}
            />
          }
          onPress={() => toggleSaved(scheme.id)}
        />
      </View>
    </Screen>
  );
}

function Row({
  label,
  value,
  highlight,
  last,
}: {
  label: string;
  value: string;
  highlight?: boolean;
  last?: boolean;
}) {
  return (
    <View style={[styles.row, !last && styles.rowBorder]}>
      <Text variant="body" color={colors.textSecondary} style={styles.rowLabel}>
        {label}
      </Text>
      <Text variant="bodyStrong" color={highlight ? colors.success : colors.text}>
        {value}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  loader: { marginTop: spacing.xxxl },
  header: { gap: spacing.sm, marginTop: spacing.md },
  chips: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.sm },
  section: { gap: spacing.sm },
  row: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    gap: spacing.md,
    paddingVertical: spacing.md,
  },
  rowLabel: { flex: 1 },
  rowBorder: { borderBottomWidth: 1, borderBottomColor: colors.border },
  bullet: { flexDirection: 'row', gap: spacing.md, paddingVertical: spacing.md },
  bulletBorder: { borderBottomWidth: 1, borderBottomColor: colors.border },
  bulletText: { flex: 1 },
  actions: { gap: spacing.sm },
});
