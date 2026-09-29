import { useState } from 'react';
import { StyleSheet, TextInput, View } from 'react-native';
import { Text } from './Text';
import { Chip } from './Chip';
import { radius, spacing, typography, useTheme } from '@/theme';
import { formatCompactCurrency, formatCurrency, parseAmountInput } from '@/utils/format';

export type AmountInputProps = {
  label: string;
  hint?: string;
  value: number;
  onChange: (value: number) => void;
  presets?: number[];
  max?: number;
};

export function AmountInput({ label, hint, value, onChange, presets = [], max }: AmountInputProps) {
  const { colors } = useTheme();
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

      <View
        style={[
          styles.field,
          {
            backgroundColor: colors.inputBackground,
            borderColor: colors.borderStrong,
          },
        ]}
      >
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
          style={[styles.input, { color: colors.text }]}
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
    borderWidth: 1.5,
    borderRadius: radius.md,
    paddingHorizontal: spacing.lg,
    minHeight: 60,
  },
  input: {
    flex: 1,
    ...typography.title,
    paddingVertical: spacing.md,
  },
  presets: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.sm, marginTop: spacing.xs },
});
