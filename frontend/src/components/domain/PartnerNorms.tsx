import { StyleSheet, View } from 'react-native';
import { useTranslation } from 'react-i18next';

import { Text } from '@/components/ui';
import type { PartnerType } from '@/api/contracts';
import { normsFor, requiredInputsFor, sourceFor } from '@/features/partners/eligibilityNorms';
import { colors, radius, spacing } from '@/theme';

/**
 * The conditions NSFDC applies before it will release funds to this kind of
 * partner — and, immediately below, the fact that we cannot check any of them.
 *
 * The two halves belong together. Listing the norms alone would read as "this
 * partner passes"; the app has no basis for that claim, and the whole reason
 * every partner is UNKNOWN is that NSFDC publishes the rules and not the
 * figures. So the missing-data note is not a footnote here, it is the point.
 *
 * Bullets are deliberately neutral dots, never checkmarks. A checkmark next to
 * an unevaluated condition is a false claim rendered in an icon.
 */

export type PartnerNormsProps = {
  type: PartnerType;
};

export function PartnerNorms({ type }: PartnerNormsProps) {
  const { t } = useTranslation();

  const norms = normsFor(type);
  const missing = requiredInputsFor(type).map((input) => t(`partners.norms.input.${input}`));

  // One caveat line per distinct source, so a norm sourced from a page that
  // no longer resolves says so rather than borrowing another norm's credibility.
  const sources = [...new Map(norms.map((n) => [sourceFor(n).id, sourceFor(n)])).values()];

  return (
    <View style={styles.wrap}>
      <Text variant="subheading">{t('partners.norms.title')}</Text>
      <Text variant="caption" color={colors.textSecondary}>
        {t('partners.norms.intro', { type: t(`partners.type.${type}`) })}
      </Text>

      <View style={styles.card}>
        {norms.map((norm) => (
          <View key={norm.id} style={styles.rule}>
            <View style={styles.bullet} />
            <Text variant="caption" style={styles.ruleText}>
              {t(norm.labelKey, norm.values)}
            </Text>
          </View>
        ))}
      </View>

      <View style={styles.gap}>
        <Text variant="bodyStrong">{t('partners.norms.missingTitle')}</Text>
        <Text variant="caption" color={colors.textSecondary}>
          {t('partners.norms.missingBody', { fields: missing.join(', ') })}
        </Text>
      </View>

      {sources.map((source) => (
        <Text key={source.id} variant="label" color={colors.textMuted}>
          {source.retrievedVia === 'WEB_ARCHIVE_SNAPSHOT'
            ? t('partners.norms.sourceSnapshot', {
                title: source.title,
                date: source.capturedOn ?? '',
              })
            : t('partners.norms.sourceLive', { title: source.title })}
        </Text>
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { gap: spacing.sm },
  gap: { gap: spacing.xs },
  card: {
    backgroundColor: colors.surface,
    borderRadius: radius.lg,
    padding: spacing.md,
    gap: spacing.sm,
  },
  rule: { flexDirection: 'row', gap: spacing.sm, alignItems: 'flex-start' },
  bullet: {
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: colors.textMuted,
    // Aligns the dot to the cap height of the first line of caption text.
    marginTop: 9,
  },
  ruleText: { flex: 1 },
});
