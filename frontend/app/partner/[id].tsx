import { ActivityIndicator, Linking, StyleSheet, View } from 'react-native';
import { useLocalSearchParams, router } from 'expo-router';
import { useTranslation } from 'react-i18next';

import { Banner, Button, Card, Chip, Screen, Text } from '@/components/ui';
import { PartnerMap, PartnerNorms } from '@/components/domain';
import { usePartner } from '@/hooks/usePartners';
import { SUPPORTED_LANGUAGES } from '@/i18n';
import { useAppStore } from '@/store/useAppStore';
import { colors, spacing } from '@/theme';

const STATUS_TONE = {
  ACCEPTING: 'success',
  LIMITED: 'warning',
  NOT_ACCEPTING: 'danger',
  UNKNOWN: 'neutral',
} as const;
const STATUS_ICON = {
  ACCEPTING: 'check',
  LIMITED: 'alert',
  NOT_ACCEPTING: 'close',
  UNKNOWN: 'info',
} as const;

export default function PartnerDetailScreen() {
  const { t } = useTranslation();
  const { id } = useLocalSearchParams<{ id: string }>();
  const language = useAppStore((s) => s.language);
  const { data: partner, isLoading, isError } = usePartner(id);

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

  if (isError || !partner) {
    return (
      <Screen>
        <Banner tone="danger" message={t('errors.notFound')} />
      </Screen>
    );
  }

  const name = partner.localizedNames?.[language] ?? partner.name;
  const status = partner.eligibility.status;

  return (
    <Screen>
      <View style={styles.header}>
        <Text variant="title">{name}</Text>
        <Text variant="caption" color={colors.textMuted}>
          {t(`partners.type.${partner.type}`)}
          {partner.branchName ? ` · ${partner.branchName}` : ''}
        </Text>
        <Chip
          label={t(`partners.status.${status}`)}
          tone={STATUS_TONE[status]}
          icon={STATUS_ICON[status]}
        />
      </View>

      {status === 'NOT_ACCEPTING' ? (
        <Banner
          tone="danger"
          message={t(partner.eligibility.reasonKey, {
            defaultValue: t('partners.eligibility.unknown'),
          })}
        />
      ) : null}

      <PartnerMap
        partners={[partner]}
        center={partner.location}
        unavailableMessage={t('partners.listView')}
      />

      <Card>
        <Text variant="body">{partner.address}</Text>
        <Text variant="caption" color={colors.textSecondary}>
          {partner.district}, {partner.stateCode} – {partner.pincode}
        </Text>
      </Card>

      <View style={styles.section}>
        <Text variant="subheading">{t('partners.handles')}</Text>
        <View style={styles.chips}>
          {partner.supportedSchemeCategories.map((category) => (
            <Chip key={category} label={t(`category.${category}`)} tone="primary" />
          ))}
        </View>
      </View>

      {partner.languagesSpoken.length > 0 ? (
        <View style={styles.section}>
          <Text variant="subheading">{t('partners.languages')}</Text>
          <View style={styles.chips}>
            {partner.languagesSpoken.map((code) => (
              <Chip
                key={code}
                label={SUPPORTED_LANGUAGES.find((l) => l.code === code)?.endonym ?? code}
                tone="neutral"
              />
            ))}
          </View>
        </View>
      ) : null}

      <PartnerNorms type={partner.type} />

      {partner.eligibility.lastAssessedAt ? (
        <Text variant="caption" color={colors.textMuted}>
          {t('partners.lastUpdated', {
            date: new Date(partner.eligibility.lastAssessedAt).toLocaleDateString(),
          })}
        </Text>
      ) : null}

      <View style={styles.actions}>
        {partner.phone ? (
          <Button
            title={t('partners.call')}
            onPress={() => Linking.openURL(`tel:${partner.phone}`).catch(() => {})}
            style={{ flex: 1 }}
          />
        ) : null}
        <Button
          title={t('partners.directions')}
          variant="outline"
          style={{ flex: 1 }}
          onPress={() => {
            const { latitude, longitude } = partner.location;
            Linking.openURL(
              `https://www.google.com/maps/search/?api=1&query=${latitude},${longitude}`,
            ).catch(() => {});
          }}
        />
        <Button
          title="Select Partner"
          variant="primary"
          style={{ flex: 1 }}
          onPress={() => {
            useAppStore.getState().updateLoanJourney({
              selectedChannelPartnerId: partner.id,
              selectedChannelPartnerName: name,
              loanStatus: 'PARTNER_SELECTED',
            });
            router.push('/(tabs)/calculator');
          }}
        />
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({
  loader: { marginTop: spacing.xxxl },
  header: { gap: spacing.sm, marginTop: spacing.md, alignItems: 'flex-start' },
  section: { gap: spacing.sm },
  chips: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.sm },
  actions: { flexDirection: 'row', gap: spacing.sm, marginTop: spacing.md },
});
