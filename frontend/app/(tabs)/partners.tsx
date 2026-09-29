import { useEffect, useMemo, useRef, useState, useCallback } from 'react';
import { ActivityIndicator, StyleSheet, View } from 'react-native';
import { router, useFocusEffect } from 'expo-router';
import { useTranslation } from 'react-i18next';
import { useQuery, useQueryClient } from '@tanstack/react-query';

import type { ChannelPartner, PartnerSearchRequest } from '@/api/contracts';
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
import { getProfile, updateProfile } from '@/api/services/profile.service';
import { spacing, useTheme } from '@/theme';
import {
  formatProfileLocation,
  profileHasAddressText,
  profileSearchPoint,
} from '@/profile/canonical';
import { partnerSearchUiState } from '@/features/partners/searchUiState';
import { buildPartnerSearchRequest, nearbyRequestMustIncludeCoordinates } from '@/features/partners/searchRequest';
import { profileKeys } from '@/features/profile/queryKeys';

const RADII = [25, 50, 100];
const SORT_OPTIONS = ['distance', 'name', 'type'] as const;
type SortOption = typeof SORT_OPTIONS[number];

export default function PartnersScreen() {
  const { t } = useTranslation();
  const { colors } = useTheme();
  const language = useAppStore((s) => s.language);
  const loanJourney = useAppStore((s) => s.loanJourney);
  const updateLoanJourney = useAppStore((s) => s.updateLoanJourney);
  const queryClient = useQueryClient();
  const enrichingRef = useRef(false);

  const {
    data: persistentProfile,
    refetch: refetchProfile,
    isPending: profilePending,
    isError: profileError,
    isFetched: profileFetched,
  } = useQuery({
    queryKey: profileKeys.profile,
    queryFn: getProfile,
    refetchOnMount: 'always',
    refetchOnWindowFocus: 'always',
  });

  useFocusEffect(
    useCallback(() => {
      void refetchProfile();
    }, [refetchProfile]),
  );

  const [viewMode, setViewMode] = useState<'nearby' | 'all'>('nearby');
  const [radiusKm, setRadiusKm] = useState(25);
  const [sortOption, setSortOption] = useState<SortOption>('name');
  const [onlyAccepting, setOnlyAccepting] = useState(true);
  const [showMap, setShowMap] = useState(false);
  const [justSelected, setJustSelected] = useState(false);
  const [resolvingSavedLocation, setResolvingSavedLocation] = useState(false);

  const handleSelectPartner = (partner: ChannelPartner) => {
    updateLoanJourney({
      selectedChannelPartnerId: partner.id,
      selectedChannelPartnerName: partner.name,
      loanStatus: 'PARTNER_SELECTED',
    });
    setJustSelected(true);
    router.push('/(tabs)/calculator');
  };

  const locPoint = profileSearchPoint(persistentProfile);
  const userLocationAvailable = Boolean(locPoint);
  const profileStatus = profilePending && !profileFetched
    ? 'loading'
    : profileError && !persistentProfile
      ? 'error'
      : 'ready';

  useEffect(() => {
    if (profileStatus !== 'ready' || locPoint || enrichingRef.current) return;
    if (!profileHasAddressText(persistentProfile)) return;
    enrichingRef.current = true;
    setResolvingSavedLocation(true);
    void updateProfile({ address: persistentProfile?.address ?? {} })
      .then(async (updated) => {
        queryClient.setQueryData(profileKeys.profile, updated);
        await queryClient.invalidateQueries({ queryKey: profileKeys.profile });
        await queryClient.invalidateQueries({ queryKey: ['partners'] });
      })
      .catch((err) => {
        console.error('[PARTNERS] failed to resolve saved address coordinates', err);
      })
      .finally(() => {
        setResolvingSavedLocation(false);
      });
  }, [locPoint, persistentProfile, profileStatus, queryClient]);

  const request: PartnerSearchRequest = useMemo(() => {
    const req = buildPartnerSearchRequest({
      viewMode,
      location: locPoint,
      radiusKm,
      onlyAccepting,
      language,
    });
    if (__DEV__ && !nearbyRequestMustIncludeCoordinates(viewMode, locPoint, req)) {
      throw new Error('Nearby search omitted saved profile coordinates');
    }
    console.log(`[PARTNERS] location source= persistentProfile.address.coordinates`);
    console.log(`[PARTNERS] latitude=${locPoint?.latitude ?? 'null'} longitude=${locPoint?.longitude ?? 'null'}`);
    console.log(`[PARTNERS] mode=${viewMode} request=`, JSON.stringify(req));
    return req;
  }, [locPoint, radiusKm, viewMode, onlyAccepting, language]);

  const nearbyNeedsLocation = viewMode === 'nearby' && !userLocationAvailable && profileStatus === 'ready' && !resolvingSavedLocation;
  const { data, isLoading, isError } = usePartnerSearch(request, !nearbyNeedsLocation && profileStatus !== 'loading');
  let partners = data?.items ?? [];
  if (nearbyNeedsLocation) {
    partners = [];
  }

  const uiState = partnerSearchUiState({
    viewMode,
    locationAvailable: userLocationAvailable,
    onlyAccepting,
    isLoading: isLoading || resolvingSavedLocation,
    isError,
    resultCount: partners.length,
    profileStatus: resolvingSavedLocation ? 'loading' : profileStatus,
  });

  const availableSortOptions = userLocationAvailable
    ? SORT_OPTIONS
    : (['name', 'type'] as const);

  useEffect(() => {
    if (!userLocationAvailable && sortOption === 'distance') {
      setSortOption('name');
    }
  }, [userLocationAvailable, sortOption]);

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
    return sorted;
  }, [partners, sortOption, userLocationAvailable]);

  const locationText = formatProfileLocation(persistentProfile);
  const locationCaption = userLocationAvailable
    ? t('partners.usingSavedProfileLocation')
    : uiState.kind === 'loading-profile'
      ? t('partners.loadingProfile')
      : uiState.kind === 'profile-unavailable'
        ? t('partners.profileUnavailable')
        : t('partners.setLocationHint');

  return (
    <Screen>
      <View style={styles.header}>
        <Text variant="title">{t('partners.findChannelPartner')}</Text>
      </View>

      <Card variant="glass" style={styles.locationCard}>
        <Text variant="bodyStrong">
          {t('partners.yourLocation')}
          <Text variant="body" color={colors.textSecondary}>
            {uiState.kind === 'loading-profile'
              ? t('common.loading')
              : locationText || t('partners.notSet')}
          </Text>
        </Text>
        <Text variant="caption" color={colors.textMuted} style={{ marginTop: spacing.xs }}>
          {locationCaption}
        </Text>
        {uiState.kind === 'idle-location-required' ? (
          <View style={{ marginTop: spacing.md }}>
            <Button
              title={t('partners.setLocationInProfile')}
              variant="outline"
              size="sm"
              onPress={() => router.push('/(tabs)/profile')}
            />
          </View>
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

      {uiState.kind === 'loading' || uiState.kind === 'loading-profile' ? (
        <ActivityIndicator
          color={colors.primary}
          style={styles.loader}
          accessibilityLabel={t('a11y.loading')}
        />
      ) : null}

      {showMap && uiState.kind === 'results' ? (
        <PartnerMap
          partners={partners}
          center={locPoint ?? undefined}
          onSelect={(partner) => router.push(`/partner/${partner.id}`)}
          unavailableMessage={t('partners.listView')}
          userLocationText={locationText}
        />
      ) : null}

      {!showMap && uiState.kind === 'profile-unavailable' ? (
        <View style={styles.empty}>
          <Text variant="subheading" center>
            {t('partners.profileUnavailable')}
          </Text>
          <Text variant="caption" color={colors.textMuted} center>
            {t('partners.profileUnavailableBody')}
          </Text>
        </View>
      ) : null}

      {!showMap && uiState.kind === 'idle-location-required' ? (
        <View style={styles.empty}>
          <Text variant="subheading" center>
            {t('partners.locationRequired')}
          </Text>
          <Text variant="caption" color={colors.textMuted} center>
            {t('partners.enableLocationOrEnterPin')}
          </Text>
        </View>
      ) : null}

      {!showMap && uiState.kind === 'empty' ? (
        <View style={styles.empty}>
          <Text variant="subheading" center>
            {uiState.reason === 'accepting'
              ? t('partners.emptyAccepting')
              : uiState.reason === 'all'
                ? t('partners.emptyAll')
                : t('partners.empty')}
          </Text>
          <Text variant="caption" color={colors.textMuted} center>
            {uiState.reason === 'accepting'
              ? t('partners.emptyAcceptingBody')
              : uiState.reason === 'all'
                ? t('partners.emptyAllBody')
                : t('partners.emptyBody')}
          </Text>
        </View>
      ) : null}

      {justSelected ? (
        <Banner
          tone="success"
          message={t('partners.partnerSelected')}
        />
      ) : null}

      {!showMap && uiState.kind === 'results' ? (
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
