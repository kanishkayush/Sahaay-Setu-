import React from 'react';
import { View, StyleSheet } from 'react-native';
import { Card, Text, Chip, Icon, Button } from '@/components/ui';
import { AssistantUICard } from '@/api/contracts';
import { colors, spacing } from '@/theme';
import { useTranslation } from 'react-i18next';

function verificationTone(status?: string): 'success' | 'warning' | 'danger' | 'neutral' {
  if (status === 'VERIFIED') return 'success';
  if (status === 'PARTIAL') return 'warning';
  if (status === 'UNVERIFIED') return 'danger';
  return 'neutral';
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
  if (!cards || cards.length === 0) return null;

  const verifyLabel = (status?: string) => {
    if (status === 'VERIFIED') return t('uiCards.verified');
    if (status === 'PARTIAL') return t('uiCards.partial');
    if (status === 'UNVERIFIED') return t('uiCards.verify');
    return status || '';
  };
  const fitLabel = (value: string) => {
    if (value === 'WITHIN_RANGE' || value === 'WITHIN_LIMIT') return t('uiCards.fitFits');
    if (value === 'OUTSIDE_RANGE') return t('uiCards.fitOutside');
    if (value === 'ABOVE_LIMIT') return t('uiCards.fitAbove');
    if (value === 'NOT_A_LOAN') return t('uiCards.fitNotALoan');
    if (value === 'UNKNOWN') return t('uiCards.fitUnknown');
    return value;
  };

  const schemeCards = cards.filter((card) => card.type === 'SCHEME_CARD');
  const otherCards = cards.filter((card) => card.type !== 'SCHEME_CARD');
  const educationSet = schemeCards.some((card) => Boolean(card.assistanceType));

  return (
    <View style={styles.container}>
      {schemeCards.length > 0 ? (
        <View style={styles.schemeGroup}>
          <Text variant="label">
            {educationSet ? t('uiCards.relatedEducationOptions') : t('uiCards.relevantOptions')}
          </Text>
          {schemeCards.map((card, idx) => (
            <Card
              key={card.schemeId || `scheme-${idx}`}
              style={[
                styles.schemeCard,
                card.verificationStatus === 'UNVERIFIED' ? styles.unverifiedCard : null,
              ]}
              onPress={
                card.schemeId && onSelectScheme
                  ? () => onSelectScheme(card.schemeId as string)
                  : undefined
              }
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
                {card.assistanceType ? (
                  <Chip label={card.assistanceType.replace(/_/g, ' ')} tone="info" />
                ) : null}
                {card.verificationStatus ? (
                  <Chip
                    label={verifyLabel(card.verificationStatus)}
                    tone={verificationTone(card.verificationStatus)}
                  />
                ) : null}
              </View>
              {card.verificationStatus === 'UNVERIFIED' ? (
                <Text variant="caption" color={colors.warningText} style={{ marginTop: spacing.xs }}>
                  {t('uiCards.verificationRequired')}
                </Text>
              ) : null}
              {card.reason ? (
                <Text variant="body" color={colors.textSecondary}>{card.reason}</Text>
              ) : null}
              {card.schemeId && onSelectScheme ? (
                <Text variant="caption" color={colors.primary} style={{ marginTop: spacing.xs }}>
                  {card.verificationStatus === 'UNVERIFIED'
                    ? t('uiCards.viewAvailableInfo')
                    : t('uiCards.viewDetails')}
                </Text>
              ) : null}
            </Card>
          ))}
        </View>
      ) : null}
      {otherCards.map((card, idx) => {
        switch (card.type) {
          case 'COMPARISON_CARD':
            return (
              <Card key={`cmp-${idx}`} style={styles.comparisonCard}>
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
              <Card key={idx} style={styles.questionCard}>
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
              <Card key={idx} style={styles.checklistCard}>
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
                    <Text variant="label" style={{ marginTop: spacing.sm }}>{t('uiCards.recommended')}</Text>
                    {card.recommended.map(doc => (
                      <Text key={doc} variant="body">・ {doc}</Text>
                    ))}
                  </>
                ) : null}
              </Card>
            );
          case 'PARTNER_CARD':
            return (
              <Card key={idx} style={styles.partnerCard}>
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
              <Card key={idx} style={styles.warningCard}>
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
  schemeCard: { borderColor: colors.primary, borderWidth: 1 },
  unverifiedCard: { borderColor: colors.warningText, borderWidth: 1 },
  questionCard: { backgroundColor: colors.surface },
  checklistCard: { backgroundColor: colors.surface },
  partnerCard: { borderColor: colors.primary, borderWidth: 1 },
  warningCard: { borderColor: colors.danger, borderWidth: 1 },
  comparisonCard: { backgroundColor: colors.surface, gap: spacing.xs },
  comparisonHeader: { flexDirection: 'row', gap: spacing.xs, marginTop: spacing.sm },
  comparisonRow: { flexDirection: 'row', gap: spacing.xs, paddingVertical: 2 },
  cmpCol: { flex: 1 },
});
