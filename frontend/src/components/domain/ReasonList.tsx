import { StyleSheet, View } from 'react-native';
import type { LanguageCode, MatchReason } from '@/api/contracts';
import { Icon, type IconName, Text } from '@/components/ui';
import { pickLocalized } from '@/i18n/localized';
import { colors, spacing } from '@/theme';

const MARKER: Record<MatchReason['kind'], string> = {
  MATCH: '✓',
  MISMATCH: '✕',
  INFO: 'ⓘ',
};
const MARKER_COLOR = {
  MATCH: colors.successText,
  MISMATCH: colors.dangerText,
  INFO: colors.infoText,
} as const;

/**
 * "Why this scheme?" — the explainability surface.
 * Every recommendation must be able to justify itself in plain language; this
 * is what makes the AI answer auditable by a beneficiary, not just by us.
 */
export function ReasonList({
  reasons,
  language,
}: {
  reasons: MatchReason[];
  language: LanguageCode;
}) {
  return (
    <View style={styles.list}>
      {reasons.map((reason, index) => (
        <View key={`${reason.kind}-${index}`} style={styles.row}>
          <View style={styles.marker}>
            <Text style={{ color: MARKER_COLOR[reason.kind], fontSize: 16, fontWeight: 'bold' }}>
              {MARKER[reason.kind]}
            </Text>
          </View>
          <Text variant="caption" color={colors.textSecondary} style={styles.text}>
            {pickLocalized(reason.text, language)}
          </Text>
        </View>
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  list: { gap: spacing.sm },
  row: { flexDirection: 'row', gap: spacing.sm, alignItems: 'flex-start' },
  marker: { width: 18, alignItems: 'center', paddingTop: 4 },
  text: { flex: 1 },
});
