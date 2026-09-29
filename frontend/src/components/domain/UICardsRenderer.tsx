import React from 'react';
import { View, StyleSheet } from 'react-native';
import { Card, Text, Chip, Icon, Button, StatRow } from '@/components/ui';
import { AssistantUICard, SchemeFitReason } from '@/api/contracts';
import { spacing, useTheme, type ColorTokens } from '@/theme';
import { useTranslation } from 'react-i18next';
import { formatMonths, formatPercent, formatStatCurrency } from '@/utils/format';
import { ragVerificationBadge } from '@/features/schemes/verification';

function verificationTone(status?: string): 'success' | 'warning' | 'danger' | 'neutral' {
  if (status === 'VERIFIED') return 'success';
  if (status === 'PARTIAL' || status === 'UNVERIFIED') return 'warning';
  return 'neutral';
}

function reasonMarks(colors: ColorTokens): Record<string, { glyph: string; color: string }> {
  return {
    MATCH: { glyph: '✓', color: colors.successText },
    MISMATCH: { glyph: '✕', color: colors.dangerText },
    INFO: { glyph: 'ℹ', color: colors.infoText },
  };
}

export function UICardsRenderer({
  cards,
  onOptionSelect,
  onSelectPartner,
  onSelectScheme,
}: {
  cards: AssistantUICard[],
  onOptionSelect?: (option: string) => void,
  onSelectPartner?: (id: string, name: string) => void,
  onSelectScheme?: (schemeId: string) => void,
}) {
  const { t } = useTranslation();
  const { colors } = useTheme();
  const REASON_MARK = reasonMarks(colors);
  if (!cards || cards.length === 0) return null;

  const verifyLabel = (status?: string) => ragVerificationBadge(status);
  const fitLabel = (value: string) => {
    if (value === 'WITHIN_RANGE' || value === 'WITHIN_LIMIT') return t('uiCards.fitFits');
    if (value === 'OUTSIDE_RANGE') return t('uiCards.fitOutside');
    if (value === 'ABOVE_LIMIT') return t('uiCards.fitAbove');
    if (value === 'NOT_A_LOAN') return t('uiCards.fitNotALoan');
    if (value === 'UNKNOWN') return t('uiCards.fitUnknown');
    return value;
  };
  const fitChip = (status?: string) => {
    if (status === 'MOST_RELEVANT' || status === 'MATCH') return t('uiCards.mostRelevant');
    if (status === 'RELATED') return t('uiCards.relatedOption');
    if (status === 'MATCHES_DETAILS') return t('uiCards.matchesDetails');
    return null;
  };

  const schemeCards = cards.filter((card): card is Extract<AssistantUICard, { type: 'SCHEME_CARD' }> => card.type === 'SCHEME_CARD');
  const otherCards = cards.filter((card) => card.type !== 'SCHEME_CARD');
  const educationSet = schemeCards.some((card) => card.domain === 'EDUCATION' || Boolean(card.assistanceType));
  const primaryCards = schemeCards.filter((card) => card.isPrimary && card.fitStatus !== 'RELATED');
  const otherSchemeCards = schemeCards.filter((card) => !primaryCards.includes(card));
  const grouped = primaryCards.length > 0 && otherSchemeCards.length > 0;
  const onlyRelated = schemeCards.length > 0 && primaryCards.length === 0 && schemeCards.every((card) => card.fitStatus === 'RELATED');

  const renderSchemeCard = (card: Extract<AssistantUICard, { type: 'SCHEME_CARD' }>, idx: number) => {
    const why: SchemeFitReason[] = card.whySelected ?? card.fitReasons ?? [];
    const stats = [
      card.verificationStatus === 'VERIFIED' && card.maxLoanAmount != null
        ? { value: formatStatCurrency(card.maxLoanAmount), label: t('uiCards.maxAssistance') }
        : null,
      card.verificationStatus === 'VERIFIED' && card.interestRatePct != null
        ? { value: formatPercent(card.interestRatePct), label: t('schemes.interestRate') }
        : null,
      card.verificationStatus === 'VERIFIED' && card.maxTenureMonths != null
        ? {
            value: formatMonths(card.maxTenureMonths, t('common.months'), t('common.years')),
            label: t('uiCards.repaymentPeriod'),
          }
        : null,
    ].filter(Boolean) as { value: string; label: string }[];
    const open = card.schemeId && onSelectScheme ? () => onSelectScheme(card.schemeId as string) : undefined;
    const chip = fitChip(card.fitStatus);

    return (
      <Card
        key={card.schemeId || `scheme-${idx}`}
        style={[
          { borderColor: colors.primary, borderWidth: 1 },
          card.verificationStatus === 'UNVERIFIED' ? { borderColor: colors.warningText, borderWidth: 1 } : null,
        ]}
        onPress={open}
        accessibilityLabel={card.schemeName}
      >
        <View style={styles.headerRow}>
          <Icon name="doc" size={20} color={colors.primary} />
          <Text variant="label" style={{ flex: 1 }}>{card.schemeName}</Text>
        </View>
        {card.organization ? (
          <Text variant="caption" color={colors.textSecondary}>{card.organization}</Text>
        ) : null}
        <View style={styles.badgeRow}>
          {chip ? <Chip label={chip} tone={card.fitStatus === 'RELATED' ? 'neutral' : 'info'} /> : null}
          {card.assistanceType ? (
            <Chip label={card.assistanceType.replace(/_/g, ' ')} tone="info" />
          ) : null}
          {card.verificationStatus ? (
            <Chip
              label={verifyLabel(card.verificationStatus)}
              tone={verificationTone(card.verificationStatus)}
              icon={card.verificationStatus === 'VERIFIED' ? 'check' : 'info'}
            />
          ) : null}
          {card.genderFit === 'MATCH' ? (
            <Chip label={t('gender.FEMALE')} tone="info" />
          ) : null}
        </View>
        {card.reason ? (
          <Text variant="body" color={colors.textSecondary}>{card.reason}</Text>
        ) : null}
        {stats.length > 0 ? <StatRow stats={stats} /> : null}
        {card.verificationStatus === 'UNVERIFIED' ? (
          <Text variant="caption" color={colors.warningText} style={{ marginTop: spacing.xs }}>
            {t('uiCards.verificationRequired')}
          </Text>
        ) : null}
        {why.length > 0 ? (
          <View style={styles.whyBlock}>
            <Text variant="label">{t('uiCards.whyThisScheme')}</Text>
            {why.map((item: SchemeFitReason, reasonIdx: number) => {
              const mark = REASON_MARK[item.kind] ?? { glyph: 'ℹ', color: colors.infoText };
              return (
                <View key={`${item.kind}-${reasonIdx}`} style={styles.whyRow}>
                  <Text style={{ color: mark.color, fontWeight: 'bold' }}>{mark.glyph}</Text>
                  <Text variant="caption" color={colors.textSecondary} style={{ flex: 1 }}>
                    {item.text}
                  </Text>
                </View>
              );
            })}
          </View>
        ) : null}
        {open ? (
          <View style={{ marginTop: spacing.sm }}>
            <Button
              title={
                card.verificationStatus === 'UNVERIFIED'
                  ? t('uiCards.viewAvailableInfo')
                  : t('uiCards.viewSchemeDetails')
              }
              variant="outline"
              size="sm"
              onPress={open}
            />
          </View>
        ) : null}
      </Card>
    );
  };

  return (
    <View style={styles.container}>
      {schemeCards.length > 0 ? (
        <View style={styles.schemeGroup}>
          {grouped ? (
            <>
              <Text variant="label">{t('uiCards.mostRelevant')}</Text>
              {primaryCards.map(renderSchemeCard)}
              <Text variant="label" style={{ marginTop: spacing.sm }}>{t('uiCards.otherRelevantOptions')}</Text>
              {otherSchemeCards.map(renderSchemeCard)}
            </>
          ) : (
            <>
              <Text variant="label">
                {onlyRelated
                  ? t('uiCards.relatedOption')
                  : educationSet
                    ? t('uiCards.relatedEducationOptions')
                    : t('uiCards.relevantOptions')}
              </Text>
              {schemeCards.map(renderSchemeCard)}
            </>
          )}
        </View>
      ) : null}
      {otherCards.map((card, idx) => {
        switch (card.type) {
          case 'COMPARISON_CARD':
            return (
              <Card key={`cmp-${idx}`} style={{ backgroundColor: colors.surface, gap: spacing.xs }}>
                <Text variant="label">{card.title || t('uiCards.comparisonTitle')}</Text>
                <View style={styles.comparisonHeader}>
                  <Text variant="caption" style={styles.cmpCol}>{t('uiCards.colScheme')}</Text>
                  <Text variant="caption" style={styles.cmpCol}>{t('uiCards.colType')}</Text>
                  <Text variant="caption" style={styles.cmpCol}>{t('uiCards.colAmount')}</Text>
                  <Text variant="caption" style={styles.cmpCol}>{t('uiCards.colIncome')}</Text>
                  <Text variant="caption" style={styles.cmpCol}>{t('uiCards.colVerify')}</Text>
                </View>
                {(card.rows ?? []).map((row) => (
                  <View key={row.schemeId || row.schemeName} style={styles.comparisonRow}>
                    <Text variant="caption" style={styles.cmpCol}>{row.schemeName}</Text>
                    <Text variant="caption" style={styles.cmpCol}>{row.assistanceType.replace(/_/g, ' ')}</Text>
                    <Text variant="caption" style={styles.cmpCol}>{fitLabel(row.amountFit)}</Text>
                    <Text variant="caption" style={styles.cmpCol}>{fitLabel(row.incomeFit)}</Text>
                    <Text variant="caption" style={styles.cmpCol}>{verifyLabel(row.verificationStatus)}</Text>
                  </View>
                ))}
              </Card>
            );
          case 'NEXT_QUESTION_CARD':
            return (
              <Card key={idx} style={{ backgroundColor: colors.surface }}>
                <Text variant="bodyStrong">{card.question}</Text>
                <View style={styles.chips}>
                  {card.options?.map(opt => (
                    <Chip key={opt} label={opt} onPress={() => onOptionSelect?.(opt)} />
                  ))}
                </View>
              </Card>
            );
          case 'DOCUMENT_CHECKLIST':
            return (
              <Card key={`docs-${idx}`} style={{ backgroundColor: colors.surface }}>
                <View style={styles.headerRow}>
                  <Icon name="doc" size={20} color={colors.text} />
                  <Text variant="label">{t('uiCards.requiredDocuments')}</Text>
                </View>
                {card.requiredByScheme?.map(doc => (
                  <Text key={doc} variant="body">・ {doc}</Text>
                ))}
                {card.requiredByPartner?.map(doc => (
                  <Text key={doc} variant="body">・ {doc}</Text>
                ))}
                {card.recommended?.length ? (
                  <>
                    <Text variant="label" style={{ marginTop: spacing.sm }}>{t('uiCards.suggestedDocuments')}</Text>
                    {card.recommended.map(doc => (
                      <Text key={doc} variant="body">・ {doc}</Text>
                    ))}
                  </>
                ) : null}
              </Card>
            );
          case 'PARTNER_CARD':
            return (
              <Card key={`partner-${idx}`} style={{ borderColor: colors.primary, borderWidth: 1 }}>
                <View style={styles.headerRow}>
                  <Icon name="pin" size={20} color={colors.primary} />
                  <Text variant="label">{card.name || t('uiCards.noPartnerSelected')}</Text>
                </View>
                {card.address ? <Text variant="body" color={colors.textSecondary}>{card.address}</Text> : null}
                {card.distanceKm !== undefined && (
                  <Text variant="caption" color={colors.primary}>{card.distanceKm} {t('uiCards.away')}</Text>
                )}
                <View style={{ marginTop: spacing.md }}>
                  <Button
                    title={t('uiCards.selectPartner')}
                    variant="outline"
                    onPress={() => {
                      if (onSelectPartner && card.partnerId) {
                        onSelectPartner(card.partnerId, card.name || '');
                      }
                    }}
                  />
                </View>
              </Card>
            );
          case 'WARNING_CARD':
            return (
              <Card key={`warn-${idx}`} style={{ borderColor: colors.danger, borderWidth: 1 }}>
                <View style={styles.headerRow}>
                  <Icon name="alert" size={20} color={colors.danger} />
                  <Text variant="bodyStrong" color={colors.danger}>{card.message}</Text>
                </View>
              </Card>
            );
          default:
            return null;
        }
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { gap: spacing.md, marginVertical: spacing.md },
  headerRow: { flexDirection: 'row', alignItems: 'center', gap: spacing.xs, marginBottom: spacing.xs },
  badgeRow: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.xs, marginVertical: spacing.xs },
  chips: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.sm, marginTop: spacing.sm },
  schemeGroup: { gap: spacing.sm },
  whyBlock: { gap: spacing.xs, marginTop: spacing.sm },
  whyRow: { flexDirection: 'row', gap: spacing.xs, alignItems: 'flex-start' },
  comparisonHeader: { flexDirection: 'row', gap: spacing.xs, marginTop: spacing.sm },
  comparisonRow: { flexDirection: 'row', gap: spacing.xs, paddingVertical: 2 },
  cmpCol: { flex: 1 },
});
