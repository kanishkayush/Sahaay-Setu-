import { useEffect, useMemo, useState } from 'react';
import { ActivityIndicator, StyleSheet, View } from 'react-native';
import { router } from 'expo-router';
import { useTranslation } from 'react-i18next';
import { useQuery } from '@tanstack/react-query';

import type { ChannelPartner, PartnerSearchRequest, PartnerType } from '@/api/contracts';
import {
  Banner,
  Button,
  Card,
  Chip,
  Screen,
  SegmentedControl,
  SettingToggle,
  Text,
} from '@/components/ui';
import { PartnerCard, PartnerMap } from '@/components/domain';
import { usePartnerSearch } from '@/hooks/usePartners';
import { useAppStore } from '@/store/useAppStore';
import { getProfile } from '@/api/services/profile.service';
import { colors, radius, spacing, typography } from '@/theme';

const RADII = [25, 50, 100];
const SORT_OPTIONS = ['distance', 'name', 'type'] as const;
type SortOption = typeof SORT_OPTIONS[number];

export default function PartnersScreen() {
  const { t } = useTranslation();
  const language = useAppStore((s) => s.language);
  const loanJourney = useAppStore((s) => s.loanJourney);
  const updateLoanJourney = useAppStore((s) => s.updateLoanJourney);

  // Canonical location source: persistent profile from backend
  const { data: persistentProfile } = useQuery({
    queryKey: ['profile'],
    queryFn: getProfile,
  });

  const [viewMode, setViewMode] = useState<'nearby' | 'all'>('nearby');
  const [radiusKm, setRadiusKm] = useState(25);
  const [sortOption, setSortOption] = useState<SortOption>('name');
  const [onlyAccepting, setOnlyAccepting] = useState(true);
  const [showMap, setShowMap] = useState(false);
  const [justSelected, setJustSelected] = useState(false);

  const handleSelectPartner = (partner: ChannelPartner) => {
    updateLoanJourney({
      selectedChannelPartnerId: partner.id,
      selectedChannelPartnerName: partner.name,
      loanStatus: 'PARTNER_SELECTED',
    });
    setJustSelected(true);
    router.push('/(tabs)/calculator');
  };

  // Strict coordinate validation — only valid, finite GPS coordinates count
  const locPoint = persistentProfile?.address?.coordinates;
  const userLocationAvailable =
    typeof locPoint?.latitude === 'number' &&
    typeof locPoint?.longitude === 'number' &&
    Number.isFinite(locPoint.latitude) &&
    Number.isFinite(locPoint.longitude) &&
    !(locPoint.latitude === 0 && locPoint.longitude === 0);

  // Log location source for diagnostics
  console.log(`[PARTNERS] location source= persistentProfile.address.coordinates`);
  console.log(`[PARTNERS] latitude=${locPoint?.latitude ?? 'null'} longitude=${locPoint?.longitude ?? 'null'}`);
  console.log(`[PARTNERS] userLocationAvailable=${userLocationAvailable}`);

  const request: PartnerSearchRequest = useMemo(() => {
    const req: PartnerSearchRequest = {
      location: userLocationAvailable ? locPoint : undefined,
      radiusKm: viewMode === 'all' ? 1000 : radiusKm,
      allPartners: viewMode === 'all',
      onlyAccepting,
      language,
    };
    console.log(`[PARTNERS] mode=${viewMode} request=`, JSON.stringify(req));
    return req;
  }, [locPoint, userLocationAvailable, radiusKm, viewMode, onlyAccepting, language]);

  const { data, isLoading, isError } = usePartnerSearch(request);
  let partners = data?.items ?? [];

  // Log partner counts
  console.log(`[PARTNERS] backend returned=${partners.length}`);

  const availableSortOptions = userLocationAvailable
    ? SORT_OPTIONS
    : (['name', 'type'] as const);

  // Fallback sort if location becomes unavailable (via useEffect, not in render body)
  useEffect(() => {
    if (!userLocationAvailable && sortOption === 'distance') {
      setSortOption('name');
    }
  }, [userLocationAvailable, sortOption]);

  // Sorting
  partners = useMemo(() => {
    const sorted = [...partners];
    if (sortOption === 'distance' && userLocationAvailable) {
      sorted.sort((a, b) => {
        const dA = a.distanceKm ?? 999999;
        const dB = b.distanceKm ?? 999999;
        return dA - dB;
      });
    } else if (sortOption === 'name') {
      sorted.sort((a, b) => a.name.localeCompare(b.name));
    } else if (sortOption === 'type') {
      sorted.sort((a, b) => a.type.localeCompare(b.type));
    }
    console.log(`[PARTNERS] frontend rendered=${sorted.length}`);
    return sorted;
  }, [partners, sortOption, userLocationAvailable]);

  const address = persistentProfile?.address;
  const locationText = [address?.pinCode, address?.district, address?.state]
    .filter(Boolean)
    .join(' · ');

  return (
    <Screen>
      <View style={styles.header}>
        <Text variant="title">{t('partners.findChannelPartner')}</Text>
      </View>

      <Card variant="glass" style={styles.locationCard}>
        <Text variant="bodyStrong">
          {t('partners.yourLocation')}
          <Text variant="body" color={colors.textSecondary}>
            {locationText || t('partners.notSet')}
          </Text>
        </Text>
        {!userLocationAvailable ? (
          <Text variant="caption" color={colors.textMuted} style={{ marginTop: spacing.xs }}>
            {t('partners.setLocationHint')}
          </Text>
        ) : null}
      </Card>

      <SegmentedControl
        segments={[
          { value: 'nearby', label: t('partners.nearby') },
          { value: 'all', label: t('partners.allPartners') },
        ]}
        value={viewMode}
        onChange={(v) => setViewMode(v as 'nearby' | 'all')}
      />

      {viewMode === 'nearby' && (
        <View style={styles.filterGroup}>
          <Text variant="label" color={colors.textMuted}>
            {t('partners.radius')}
          </Text>
          <View style={styles.chipRow}>
            {RADII.map((km) => (
              <Chip
                key={km}
                label={`${km} km`}
                tone="primary"
                selected={radiusKm === km}
                onPress={() => setRadiusKm(km)}
              />
            ))}
          </View>
        </View>
      )}

      <View style={styles.filterGroup}>
        <Text variant="label" color={colors.textMuted}>
          {t('partners.sortBy')}
        </Text>
        <View style={styles.chipRow}>
          {availableSortOptions.map((opt) => (
            <Chip
              key={opt}
              label={
                opt === 'distance'
                  ? t('partners.distanceLabel')
                  : opt === 'name'
                    ? t('partners.nameLabel')
                    : t('partners.typeLabel')
              }
              tone="primary"
              selected={sortOption === opt}
              onPress={() => setSortOption(opt as SortOption)}
            />
          ))}
        </View>
      </View>

      <SegmentedControl
        segments={[
          { value: 'list' as const, label: t('partners.listView') },
          { value: 'map' as const, label: t('partners.mapView') },
        ]}
        value={showMap ? 'map' : 'list'}
        onChange={(v) => setShowMap(v === 'map')}
      />

      <SettingToggle
        title={t('partners.onlyAccepting')}
        subtitle={t('partners.onlyAcceptingHint')}
        value={onlyAccepting}
        onChange={setOnlyAccepting}
      />

      {data?.fallbackUsed ? (
        <Banner tone="warning" message={t('partners.fallbackWarning')} />
      ) : null}

      {isError ? <Banner tone="danger" message={t('errors.generic')} /> : null}

      {isLoading ? (
        <ActivityIndicator
          color={colors.primary}
          style={styles.loader}
          accessibilityLabel={t('a11y.loading')}
        />
      ) : null}

      {showMap ? (
        <PartnerMap
          partners={partners}
          center={locPoint ?? undefined}
          onSelect={(partner) => router.push(`/partner/${partner.id}`)}
          unavailableMessage={t('partners.listView')}
          userLocationText={locationText}
        />
      ) : null}

      {!showMap && !isLoading && !isError && partners.length === 0 ? (
        <View style={styles.empty}>
          {viewMode === 'nearby' && !userLocationAvailable ? (
            <>
              <Text variant="subheading" center>
                {t('partners.locationRequired')}
              </Text>
              <Text variant="caption" color={colors.textMuted} center>
                {t('partners.enableLocationOrEnterPin')}
              </Text>
            </>
          ) : (
            <>
              <Text variant="subheading" center>
                {t('partners.empty')}
              </Text>
              <Text variant="caption" color={colors.textMuted} center>
                {t('partners.emptyBody')}
              </Text>
            </>
          )}
        </View>
      ) : null}

      {justSelected ? (
        <Banner
          tone="success"
          message={t('partners.partnerSelected')}
        />
      ) : null}

      {!showMap ? (
        <>
          <View style={{ marginTop: spacing.md, marginBottom: spacing.sm }}>
            <Text variant="subheading">
              {t('partners.foundCount', { count: partners.length })}
            </Text>
          </View>
          <View style={styles.list}>
            {partners.map((partner) => (
              <PartnerCard
                key={partner.id}
                partner={partner}
                language={language}
                onPress={() => router.push(`/partner/${partner.id}`)}
                onSelect={handleSelectPartner}
                isSelected={loanJourney.selectedChannelPartnerId === partner.id}
              />
            ))}
          </View>
        </>
      ) : null}
    </Screen>
  );
}

const styles = StyleSheet.create({
  header: { gap: spacing.xs, marginTop: spacing.md },
  locationCard: { marginVertical: spacing.md },
  filterGroup: { gap: spacing.sm, marginVertical: spacing.sm },
  chipRow: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.sm },
  list: { gap: spacing.md },
  loader: { marginTop: spacing.xl },
  empty: { gap: spacing.xs, marginTop: spacing.xl },
});
