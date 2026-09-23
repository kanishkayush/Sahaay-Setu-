import React from 'react';
import { View, StyleSheet } from 'react-native';
import { Card, Text, Chip, Icon, Button } from '@/components/ui';
import { AssistantUICard } from '@/api/contracts';
import { colors, spacing } from '@/theme';
import { useTranslation } from 'react-i18next';

export function UICardsRenderer({ cards, onOptionSelect, onSelectPartner }: { cards: AssistantUICard[], onOptionSelect?: (option: string) => void, onSelectPartner?: (id: string, name: string) => void }) {
  const { t } = useTranslation();
  if (!cards || cards.length === 0) return null;

  return (
    <View style={styles.container}>
      {cards.map((card, idx) => {
        switch (card.type) {
          case 'SCHEME_CARD':
            return (
              <Card key={idx} style={styles.schemeCard}>
                <View style={styles.headerRow}>
                  <Icon name="check-circle" size={20} color={colors.success} />
                  <Text variant="label" style={{ flex: 1 }}>{card.schemeName}</Text>
                </View>
                <Text variant="body" color={colors.textSecondary}>{card.reason}</Text>
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
                <Text variant="label">{t('uiCards.requiredDocuments')}</Text>
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
                  <Icon name="map-pin" size={20} color={colors.primary} />
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
                  <Icon name="alert-triangle" size={20} color={colors.danger} />
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
  chips: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.sm, marginTop: spacing.sm },
  schemeCard: { borderColor: colors.success, borderWidth: 1 },
  questionCard: { backgroundColor: colors.surface },
  checklistCard: { backgroundColor: colors.surface },
  partnerCard: { borderColor: colors.primary, borderWidth: 1 },
  warningCard: { borderColor: colors.danger, borderWidth: 1 },
});
