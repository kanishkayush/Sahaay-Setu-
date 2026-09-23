import { useState } from 'react';
import { StyleSheet, TextInput, View } from 'react-native';
import { Text } from './Text';
import { Chip } from './Chip';
import { colors, radius, spacing, typography } from '@/theme';
import { formatCompactCurrency, formatCurrency, parseAmountInput } from '@/utils/format';

export type AmountInputProps = {
  label: string;
  hint?: string;
  value: number;
  onChange: (value: number) => void;
  /** Tappable shortcuts — vital for users uncomfortable with number keypads. */
  presets?: number[];
  max?: number;
};

/**
 * Money entry. Shows the amount back in words-ish form ("₹1.4 lakh") under the
 * field, because a long digit string is easy to get wrong by an order of
 * magnitude — and that mistake changes which scheme someone is matched to.
 */
export function AmountInput({ label, hint, value, onChange, presets = [], max }: AmountInputProps) {
  const [text, setText] = useState(value > 0 ? String(value) : '');

  const commit = (raw: string) => {
    setText(raw);
    const parsed = parseAmountInput(raw);
    onChange(max ? Math.min(parsed, max) : parsed);
  };

  return (
    <View style={styles.wrapper}>
      <Text variant="subheading">{label}</Text>
      {hint ? (
        <Text variant="caption" color={colors.textMuted}>
          {hint}
        </Text>
      ) : null}

      <View style={styles.field}>
        <Text variant="heading" color={colors.textSecondary}>
          ₹
        </Text>
        <TextInput
          value={text}
          onChangeText={commit}
          keyboardType="number-pad"
          inputMode="numeric"
          placeholder="0"
          placeholderTextColor={colors.textMuted}
          style={styles.input}
          accessibilityLabel={label}
          maxFontSizeMultiplier={1.4}
        />
      </View>

      {value > 0 ? (
        <Text variant="caption" color={colors.primary}>
          {formatCurrency(value)} · {formatCompactCurrency(value)}
        </Text>
      ) : null}

      {presets.length > 0 ? (
        <View style={styles.presets}>
          {presets.map((preset) => (
            <Chip
              key={preset}
              label={formatCompactCurrency(preset)}
              tone="primary"
              selected={value === preset}
              onPress={() => commit(String(preset))}
            />
          ))}
        </View>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  wrapper: { gap: spacing.sm },
  field: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing.sm,
    backgroundColor: colors.surface,
    borderWidth: 1.5,
    borderColor: colors.borderStrong,
    borderRadius: radius.md,
    paddingHorizontal: spacing.lg,
    minHeight: 60,
  },
  input: {
    flex: 1,
    ...typography.title,
    color: colors.text,
    paddingVertical: spacing.md,
  },
  presets: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.sm, marginTop: spacing.xs },
});
