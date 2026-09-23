// @ts-nocheck
import { useEffect, useMemo, useState } from 'react';
import { ActivityIndicator, ScrollView, StyleSheet, View } from 'react-native';
import { router } from 'expo-router';
import { useTranslation } from 'react-i18next';

import type { OfficialCategory } from '@/api/contracts';
import { Banner, Button, Card, Chip, Icon, Screen, Text } from '@/components/ui';
import { ReasonList, SchemeCard } from '@/components/domain';
import { useRecommendations } from '@/hooks/useRecommendations';
import { pickLocalized } from '@/i18n/localized';
import { useAppStore } from '@/store/useAppStore';
import { colors, spacing } from '@/theme';
import { formatCompactCurrency, formatCurrency, formatPercent } from '@/utils/format';

export default function ResultsScreen() {
  const { t } = useTranslation();
  const profile = useAppStore((s) => s.profile);
  const language = useAppStore((s) => s.language);
  const { mutate, data, isPending, isError } = useRecommendations();
  const [filter, setFilter] = useState<OfficialCategory | null>(null);

  useEffect(() => {
    if (profile) mutate({ profile, language, limit: 5 });
  }, [profile, language, mutate]);

  // Every hook must run on each render — these sit above the early return below.
  const all = useMemo(() => data?.recommendations ?? [], [data]);

  /** Only offer a filter for categories actually present in these results. */
  const categories = useMemo(() => [...new Set(all.map((r) => r.scheme.officialCategory))], [all]);
  const recommendations = filter ? all.filter((r) => r.scheme.officialCategory === filter) : all;

  if (!profile) {
    return (
      <Screen>
        <Banner tone="warning" message={t('errors.notFound')} />
        <Button title={t('recommender.title')} onPress={() => router.replace('/recommend')} />
      </Screen>
    );
  }

  return (
    <Screen>
      {isPending ? (
        <View style={styles.loading}>
          <ActivityIndicator size="large" color={colors.primary} />
          <Text variant="body" color={colors.textSecondary}>
            {t('recommender.analysing')}
          </Text>
        </View>
      ) : null}

      {isError ? <Banner tone="danger" message={t('errors.generic')} /> : null}

      {data ? (
        <>
          <View style={styles.header}>
            <Text variant="title">{t('recommender.resultsTitle')}</Text>
          </View>

          {/* What produced these matches, and a way straight back to change it. */}
          <Card variant="glass">
            <View style={styles.basedOn}>
              <View style={styles.basedOnBody}>
                <Text variant="label" color={colors.textMuted} style={{ marginBottom: spacing.sm }}>
                  {t('recommender.basedOnYourDetails')}
                </Text>
                <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: spacing.xs }}>
                  {([
                    t(`projectType.${profile.projectType}`),
                    `${formatCurrency(profile.estimatedProjectCost)} ${t('recommender.projectWord')}`,
                    `${formatCurrency(profile.annualFamilyIncome)} ${t('recommender.incomeWord')}`,
                    t(`education.${profile.educationStatus}`),
                    profile.gender ? t(`gender.${profile.gender}`) : null,
                  ].filter(Boolean) as string[]).map((detail, i) => (
                    <Chip key={i} label={detail} tone="neutral" />
                  ))}
                </View>
              </View>
              <Button
                title=""
                variant="primary"
                size="sm"
                fullWidth={false}
                icon={<Icon name="edit" size={20} color={colors.surface} />}
                accessibilityLabel={t('recommender.editAnswers')}
                onPress={() => router.replace('/recommend')}
              />
            </View>
          </Card>

          {categories.length > 1 ? (
            <ScrollView
              horizontal
              showsHorizontalScrollIndicator={false}
              contentContainerStyle={styles.filters}
            >
              <Chip
                label={t('schemes.filterAll')}
                selected={filter === null}
                onPress={() => setFilter(null)}
              />
              {categories.map((category) => (
                <Chip
                  key={category}
                  label={t(`category.${category}`)}
                  selected={filter === category}
                  onPress={() => setFilter(category)}
                />
              ))}
            </ScrollView>
          ) : null}

          {data.offline ? <Chip label={t('common.offline')} tone="warning" icon="alert" /> : null}

          {recommendations.length === 0 ? (
            <Card>
              <Text variant="subheading">{t('recommender.noResults')}</Text>
              <Text variant="caption" color={colors.textSecondary} style={styles.gap}>
                {t('recommender.noResultsBody')}
              </Text>
            </Card>
          ) : null}

          <View style={styles.list}>
            {recommendations.map((recommendation, index) => {
              const isTop = index === 0;
              return (
              <View key={recommendation.scheme.id} style={styles.resultBlock}>
                {isTop && (
                  <Text variant="subheading" style={{ marginTop: spacing.md, marginBottom: spacing.xs }}>{t('recommender.recommendedForYou')}</Text>
                )}
                {!isTop && index === 1 && (
                  <Text variant="subheading" style={{ marginTop: spacing.xl, marginBottom: spacing.xs }}>{t('recommender.otherApplicableSchemes')}</Text>
                )}

                <SchemeCard
                  scheme={recommendation.scheme}
                  language={language}
                  recommendation={recommendation}
                  rank={index + 1}
                  onPress={() => router.push(`/scheme/${recommendation.scheme.id}`)}
                />

                <Card variant="glass">
                  <Text variant="subheading">{t('recommender.whyThisScheme')}</Text>
                  <View style={styles.gap}>
                    <ReasonList reasons={recommendation.reasons} language={language} />
                  </View>

                  {recommendation.citations.length > 0 ? (
                    <View style={styles.citations}>
                      <Text variant="label" color={colors.textMuted}>
                        {t('assistant.sources')}
                      </Text>
                      {recommendation.citations.map((citation) => (
                        <Text key={citation.id} variant="caption" color={colors.textSecondary}>
                          • {citation.title}
                          {citation.locator ? ` — ${citation.locator}` : ''}
                        </Text>
                      ))}
                    </View>
                  ) : null}

                  <View style={styles.actions}>
                    <Button
                      title={t('recommender.calculateEmi')}
                      variant="primary"
                      size="sm"
                      fullWidth={false}
                      style={styles.action}
                      onPress={() =>
                        router.push({
                          pathname: '/(tabs)/calculator',
                          params: {
                            principal: recommendation.eligibleLoanAmount,
                            rate: recommendation.applicableInterestRatePct,
                            tenure: recommendation.suggestedTenureMonths,
                            moratorium: recommendation.suggestedMoratoriumMonths,
                            scheme: pickLocalized(
                              recommendation.scheme.name,
                              language,
                              recommendation.scheme.code,
                            ),
                          },
                        })
                      }
                    />
                    <Button
                      title={t('recommender.findPartner')}
                      variant="primary"
                      size="sm"
                      fullWidth={false}
                      style={styles.action}
                      onPress={() => router.push('/(tabs)/partners')}
                    />
                  </View>
                </Card>

                {isTop && recommendations.length === 1 && data.nearMisses.length > 0 && (
                  <Card variant="glass" style={{ marginTop: spacing.md }}>
                    <Text variant="body" color={colors.textSecondary}>
                      Based on the information provided, {pickLocalized(recommendation.scheme.name, language, recommendation.scheme.code)} is the only scheme currently matching your selected purpose and project profile. Other schemes require different project or eligibility conditions.
                    </Text>
                  </Card>
                )}
              </View>
            )})}
          </View>

          {data.nearMisses.length > 0 ? (
            <View style={styles.section}>
              <Text variant="subheading">{t('recommender.nearMisses')}</Text>
              {data.nearMisses.map((miss) => (
                <Card key={miss.scheme.id}>
                  <Text variant="bodyStrong">
                    {pickLocalized(miss.scheme.name, language, miss.scheme.code)}
                  </Text>
                  <Text variant="caption" color={colors.textMuted}>
                    {miss.scheme.maxLoanAmount != null ? formatCompactCurrency(miss.scheme.maxLoanAmount) : t('common.notSpecified', 'Not specified')} ·{' '}
                    {formatPercent(miss.scheme.interestRateMinPct)}
                  </Text>
                  <View style={styles.gap}>
                    <ReasonList reasons={miss.reasons.slice(0, 2)} language={language} />
                  </View>
                </Card>
              ))}
            </View>
          ) : null}

          <Button
            title={t('recommender.editAnswers')}
            variant="ghost"
            onPress={() => router.replace('/recommend')}
          />
        </>
      ) : null}
    </Screen>
  );
}

const styles = StyleSheet.create({
  loading: { alignItems: 'center', gap: spacing.md, marginTop: spacing.xxxl },
  header: { gap: spacing.xs, marginTop: spacing.md },
  basedOn: { flexDirection: 'row', alignItems: 'flex-start', gap: spacing.md },
  basedOnBody: { flex: 1, gap: spacing.xs },
  basedOnLabel: { textTransform: 'uppercase' },
  filters: { gap: spacing.sm, paddingRight: spacing.lg },
  list: { gap: spacing.xl },
  resultBlock: { gap: spacing.sm },
  section: { gap: spacing.md },
  gap: { marginTop: spacing.sm },
  citations: { gap: 2, marginTop: spacing.md },
  actions: { flexDirection: 'row', gap: spacing.sm, marginTop: spacing.lg },
  action: { flex: 1 },
});
