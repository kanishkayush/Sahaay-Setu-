import React from 'react';
import { StyleSheet, View } from 'react-native';
import type { ChannelPartner, GeoPoint } from '@/api/contracts';
import { Icon, Text } from '@/components/ui';
import { colors, radius, spacing } from '@/theme';
import { useTranslation } from 'react-i18next';
import { isValidCoordinate } from '@/utils/geo';

/**
 * Map view for the partner locator.
 *
 * `react-native-maps` is loaded lazily and defensively: it needs native code, so
 * it is unavailable on web and can be missing in a bare Expo Go client. Rather
 * than crashing the whole Partners tab — the list view is the primary
 * experience anyway — we degrade to an explanatory placeholder.
 */

type MapsModule = {
  default: React.ComponentType<Record<string, unknown>>;
  Marker: React.ComponentType<Record<string, unknown>>;
};

let maps: MapsModule | null = null;
try {
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  maps = require('react-native-maps') as MapsModule;
} catch {
  maps = null;
}

/** Marker pins take the theme's semantic fills, not hand-picked hex. */
const MARKER_COLOR = {
  ACCEPTING: colors.success,
  LIMITED: colors.warning,
  NOT_ACCEPTING: colors.danger,
  UNKNOWN: colors.textMuted,
} as const;

export type PartnerMapProps = {
  partners: ChannelPartner[];
  center?: GeoPoint;
  onSelect?: (partner: ChannelPartner) => void;
  unavailableMessage: string;
  userLocationText?: string;
};

export function PartnerMap({ partners, center, onSelect, unavailableMessage, userLocationText }: PartnerMapProps) {
  const { t } = useTranslation();
  if (!maps) {
    return (
      <View style={styles.placeholder}>
        <Icon name="pin" size={28} color={colors.textMuted} />
        <Text variant="caption" color={colors.textMuted} center>
          {unavailableMessage}
        </Text>
      </View>
    );
  }

  const MapView = maps.default;
  const Marker = maps.Marker;

  const validPartners = partners.filter((p) => isValidCoordinate(p.location));
  console.log(`[PARTNER MAP] total partners=${partners.length}`);
  console.log(`[PARTNER MAP] valid coordinate partners=${validPartners.length}`);
  console.log(`[PARTNER MAP] invalid coordinate partners=${partners.length - validPartners.length}`);
  
  if (validPartners.length === 0) {
    return (
      <View style={styles.placeholder}>
        <Icon name="pin" size={28} color={colors.textMuted} />
        <Text variant="caption" color={colors.textMuted} center>
          {t('partners.noVerifiedMapPartners')}
        </Text>
      </View>
    );
  }

  const origin = center ?? validPartners[0]?.location ?? { latitude: 20.5937, longitude: 78.9629 };

  const mapRef = React.useRef<any>(null);

  React.useEffect(() => {
    if (mapRef.current && maps) {
      const coords = validPartners.map((p) => p.location!);
      if (center) coords.push(center);
      if (coords.length > 0) {
        // slight delay to let layout settle
        setTimeout(() => {
          mapRef.current?.fitToCoordinates(coords, {
            edgePadding: { top: 50, right: 50, bottom: 50, left: 50 },
            animated: true,
          });
        }, 500);
      }
    }
  }, [validPartners, center]);

  try {
    return (
      <View style={styles.container}>
        <MapView
          ref={mapRef}
          style={StyleSheet.absoluteFill}
          initialRegion={{
            latitude: origin.latitude,
            longitude: origin.longitude,
            latitudeDelta: 0.4,
            longitudeDelta: 0.4,
          }}
        >
          {center ? (
            <Marker
              coordinate={center}
              title={t('partners.youAreHere')}
              pinColor={colors.primary}
            />
          ) : null}
          {validPartners.map((partner) => (
            <Marker
              key={partner.id}
              coordinate={partner.location!}
              title={partner.name}
              description={partner.address}
              pinColor={MARKER_COLOR[partner.eligibility.status]}
              onCalloutPress={() => onSelect?.(partner)}
            />
          ))}
        </MapView>
      </View>
    );
  } catch (err) {
    console.error(`[PARTNER MAP] map initialization error:`, err);
    return (
      <View style={styles.placeholder}>
        <Icon name="pin" size={28} color={colors.textMuted} />
        <Text variant="caption" color={colors.textMuted} center>
          {t('partners.mapRenderingFailed')}
        </Text>
      </View>
    );
  }
}

const styles = StyleSheet.create({
  container: {
    height: 320,
    borderRadius: radius.lg,
    overflow: 'hidden',
    borderWidth: 1,
    borderColor: colors.border,
  },
  placeholder: {
    height: 200,
    alignItems: 'center',
    justifyContent: 'center',
    gap: spacing.sm,
    padding: spacing.lg,
    backgroundColor: colors.surfaceAlt,
    borderRadius: radius.lg,
    borderWidth: 1,
    borderColor: colors.border,
    borderStyle: 'dashed',
  },
});
