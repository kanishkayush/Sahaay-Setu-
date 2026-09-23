// @ts-nocheck
import { useMemo, useState } from 'react';
import { ActivityIndicator, ScrollView, StyleSheet, View } from 'react-native';
import { router } from 'expo-router';
import { useTranslation } from 'react-i18next';

import type { OfficialCategory } from '@/api/contracts';
import { Banner, Chip, Screen, Text } from '@/components/ui';
import { SchemeCard } from '@/components/domain';
import { useSchemes } from '@/hooks/useSchemes';
import { pickLocalized } from '@/i18n/localized';
import { useAppStore } from '@/store/useAppStore';
import { colors, spacing } from '@/theme';

const CATEGORIES: OfficialCategory[] = [
  'NGO',
  'EDUCATION',
  'ECONOMIC_DEVELOPMENT',
  'SOCIAL_EMPOWERMENT'
];

export default function SchemesScreen() {
  const { t } = useTranslation();
  const language = useAppStore((s) => s.language);
  const { data, isLoading, isError } = useSchemes();
  const [filter, setFilter] = useState<OfficialCategory | null>(null);

  const schemes = useMemo(() => {
    if (!data) return [];
    return filter ? data.items.filter((s) => s.officialCategory === filter) : data.items;
  }, [data, filter]);

  return (
    <Screen>
      <View style={styles.header}>
        <Text variant="title">{t('schemes.title')}</Text>
        <Text variant="caption" color={colors.textSecondary}>
          {t('schemes.subtitle')}
        </Text>
      </View>

      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        contentContainerStyle={styles.filters}
      >
        <Chip
          label={t('schemes.filterAll')}
          tone="primary"
          selected={filter === null}
          onPress={() => setFilter(null)}
        />
        {CATEGORIES.map((category) => {
          let label = category;
          switch (category) {
            case 'NGO': label = 'NGOs'; break;
            case 'EDUCATION': label = 'Education'; break;
            case 'ECONOMIC_DEVELOPMENT': label = 'Economic Development'; break;
            case 'SOCIAL_EMPOWERMENT': label = 'Social Empowerment'; break;
          }
          return (
            <Chip
              key={category}
              label={label}
              tone="primary"
              selected={filter === category}
              onPress={() => setFilter(category)}
            />
          );
        })}
      </ScrollView>

      {data?.dataDisclaimer ? (
        <Banner tone="warning" message={pickLocalized(data.dataDisclaimer, language)} />
      ) : null}

      {isLoading ? (
        <ActivityIndicator
          color={colors.primary}
          style={styles.loader}
          accessibilityLabel={t('a11y.loading')}
        />
      ) : null}

      {isError ? <Banner tone="danger" message={t('errors.generic')} /> : null}

      {!isLoading && schemes.length === 0 ? (
        <Text variant="body" color={colors.textMuted} center style={styles.empty}>
          {t('schemes.empty')}
        </Text>
      ) : null}

      <View style={styles.list}>
        {schemes.map((scheme) => (
          <SchemeCard
            key={scheme.id}
            scheme={scheme}
            language={language}
            onPress={() => router.push(`/scheme/${scheme.id}`)}
          />
        ))}
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({
  header: { gap: spacing.xs, marginTop: spacing.md },
  filters: { gap: spacing.sm, paddingRight: spacing.lg },
  list: { gap: spacing.md },
  loader: { marginTop: spacing.xl },
  empty: { marginTop: spacing.xl },
});
