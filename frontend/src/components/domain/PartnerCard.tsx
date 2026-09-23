import { Linking, Pressable, StyleSheet, View } from 'react-native';
import { useTranslation } from 'react-i18next';

import type { ChannelPartner, LanguageCode } from '@/api/contracts';
import { Button, Card, Chip, Icon, Text } from '@/components/ui';
import { colors, radius, spacing } from '@/theme';
import { formatDistance, isValidCoordinate } from '@/utils/geo';
import { formatPercent } from '@/utils/format';

/**
 * Channel Partner card, per the Open Design iOS sheet: a type badge, the
 * distance, the accepting status, and the fund-health figures as key–value rows.
 *
 * Showing NPA to the user is deliberate transparency — it is the number that
 * decides whether their application will actually move, and requirement R3
 * exists because of it.
 *
 * The card is NOT pressable as a whole: it carries Call and Directions buttons,
 * and nesting pressables is invalid on web and reads as overlapping targets to a
 * screen reader. The info region navigates; the action row is a sibling.
 */

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

export type PartnerCardProps = {
  partner: ChannelPartner;
  language: LanguageCode;
  onPress?: () => void;
  /** Called when the user explicitly selects this partner for their loan journey. */
  onSelect?: (partner: ChannelPartner) => void;
  /** Whether this partner is currently selected in the loan journey. */
  isSelected?: boolean;
};

export function PartnerCard({ partner, language, onPress, onSelect, isSelected }: PartnerCardProps) {
  const { t } = useTranslation();
  const name = partner.localizedNames?.[language] ?? partner.name;
  const status = partner.eligibility.status;

  const call = () => {
    if (partner.phone) Linking.openURL(`tel:${partner.phone}`).catch(() => {});
  };

  const hasLocation = isValidCoordinate(partner.location);

  const directions = () => {
    const loc = partner.location;
    if (!isValidCoordinate(loc)) return;
    const { latitude, longitude } = loc;
    console.log(`[PARTNER DIRECTIONS] ID=${partner.id} RAW_LOC=${JSON.stringify(loc)} NORMALIZED=${latitude},${longitude}`);
    
    const url = `https://www.google.com/maps/dir/?api=1&destination=${latitude},${longitude}`;
    console.log(`[PARTNER DIRECTIONS] URL=${url}`);
    
    Linking.openURL(url).catch((e) => {
      console.error('[PARTNER DIRECTIONS] Failed to open URL', e);
    });
  };

  return (
    <Card variant="glass" padded={false}>
      <Pressable
        accessibilityRole="button"
        accessibilityLabel={name}
        onPress={onPress}
        style={({ pressed }) => [styles.info, pressed && styles.pressed]}
      >
        <View style={styles.header}>
          <View style={styles.typeBadge}>
            <Text variant="label" color={colors.textSecondary}>
              {partner.type === 'NBFC_MFI' ? 'NBFC' : partner.type}
            </Text>
          </View>

          <View style={styles.titleBlock}>
            <Text variant="subheading">{name}</Text>
            {partner.branchName ? (
              <Text variant="caption" color={colors.textMuted}>
                {partner.branchName}
              </Text>
            ) : null}
          </View>

          {partner.distanceKm !== undefined && partner.distanceKm !== null ? (
            <Text variant="label" color={colors.textMuted}>
              {formatDistance(partner.distanceKm)}
            </Text>
          ) : (
            <Text variant="label" color={colors.textMuted}>
              {t('partners.distanceUnavailable')}
            </Text>
          )}
        </View>

        <Text variant="caption" color={colors.textSecondary} style={styles.address}>
          {partner.address} · {partner.pincode}
        </Text>

        <View style={styles.statusRow}>
          <Chip
            label={t(`partners.status.${status}`)}
            tone={STATUS_TONE[status]}
            icon={STATUS_ICON[status]}
          />
        </View>

        {/* The figures behind the status — why this partner can or cannot help. */}
        <View style={styles.kv}>
          <Row label={t('partners.typeLabel')} value={t(`partners.type.${partner.type}`)} />
          {partner.eligibility.npaPct !== undefined ? (
            <Row
              label={t('partners.npa')}
              value={formatPercent(partner.eligibility.npaPct)}
              tone={partner.eligibility.npaPct >= 10 ? colors.dangerText : colors.text}
              last
            />
          ) : null}
        </View>

        <Text variant="caption" color={colors.textMuted} style={styles.reason}>
          {t(partner.eligibility.reasonKey, { defaultValue: t('partners.eligibility.unknown') })}
        </Text>
      </Pressable>

      <View style={styles.actions}>
        {partner.phone ? (
          <Button
            title={t('partners.call')}
            variant="outline"
            size="sm"
            fullWidth={false}
            style={styles.action}
            icon={<Icon name="phone" size={17} color={colors.primary} strokeWidth={2} />}
            onPress={call}
          />
        ) : null}
        <Button
          title={hasLocation ? t('partners.directions') : t('partners.locationUnavailable')}
          variant="outline"
          size="sm"
          disabled={!hasLocation}
          fullWidth={false}
          style={styles.action}
          icon={hasLocation ? <Icon name="nav" size={17} color={colors.primary} strokeWidth={2} /> : undefined}
          onPress={directions}
        />
        {onSelect ? (
          <Button
            title={isSelected ? `\u2713 ${t('common.selected', 'Selected')}` : t('partners.selectPartner')}
            variant={isSelected ? ('primary' as const) : ('outline' as const)}
            size="sm"
            fullWidth={false}
            style={isSelected ? StyleSheet.flatten([styles.action, styles.selectedBtn]) : styles.action}
            onPress={() => onSelect(partner)}
          />
        ) : null}
      </View>
    </Card>
  );
}

function Row({
  label,
  value,
  tone = colors.text,
  last,
}: {
  label: string;
  value: string;
  tone?: string;
  last?: boolean;
}) {
  return (
    <View style={[styles.kvRow, !last && styles.kvDivider]}>
      <Text variant="caption" color={colors.textMuted}>
        {label}
      </Text>
      <Text variant="bodyStrong" color={tone}>
        {value}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  info: { padding: spacing.lg },
  pressed: { opacity: 0.85 },
  header: { flexDirection: 'row', alignItems: 'flex-start', gap: spacing.md },
  typeBadge: {
    minWidth: 52,
    paddingHorizontal: spacing.sm,
    paddingVertical: spacing.sm,
    borderRadius: radius.sm,
    backgroundColor: colors.background,
    alignItems: 'center',
    justifyContent: 'center',
  },
  titleBlock: { flex: 1, gap: 2 },
  address: { marginTop: spacing.md },
  statusRow: { flexDirection: 'row', marginTop: spacing.md },
  kv: { marginTop: spacing.md },
  kvRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    gap: spacing.md,
    paddingVertical: spacing.sm,
  },
  kvDivider: { borderBottomWidth: 1, borderBottomColor: colors.borderSoft },
  reason: { marginTop: spacing.sm },
  actions: {
    flexDirection: 'row',
    gap: spacing.sm,
    paddingHorizontal: spacing.lg,
    paddingBottom: spacing.lg,
  },
  action: { flex: 1 },
  selectedBtn: { backgroundColor: colors.success },
});
