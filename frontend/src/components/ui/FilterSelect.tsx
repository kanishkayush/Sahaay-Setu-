import { Pressable, StyleSheet, TextInput, View } from 'react-native';
import { useMemo, useState } from 'react';

import { Text } from './Text';
import { Icon } from './Icon';
import { radius, spacing, useTheme } from '@/theme';

export type FilterSelectOption = {
  value: string;
  label: string;
};

export type FilterSelectProps = {
  label: string;
  value: string;
  options: FilterSelectOption[];
  onChange: (value: string) => void;
  searchable?: boolean;
  searchPlaceholder?: string;
  testID?: string;
};

export function FilterSelect({
  label,
  value,
  options,
  onChange,
  searchable = false,
  searchPlaceholder = 'Search',
  testID,
}: FilterSelectProps) {
  const { colors } = useTheme();
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');
  const selected = options.find((option) => option.value === value) ?? options[0];
  const filtered = useMemo(() => {
    const needle = query.trim().toLowerCase();
    if (!needle) return options;
    return options.filter((option) => option.label.toLowerCase().includes(needle) || option.value.toLowerCase().includes(needle));
  }, [options, query]);

  return (
    <View style={styles.wrap} testID={testID}>
      <Text variant="label" color={colors.textMuted}>
        {label}
      </Text>
      <Pressable
        accessibilityRole="button"
        accessibilityState={{ expanded: open }}
        accessibilityLabel={`${label}: ${selected?.label ?? value}`}
        onPress={() => setOpen((current) => !current)}
        style={[
          styles.trigger,
          {
            backgroundColor: colors.inputBackground,
            borderColor: colors.border,
          },
        ]}
      >
        <Text variant="body" color={colors.text} style={styles.triggerText}>
          {selected?.label ?? value}
        </Text>
        <Icon name={open ? 'up' : 'down'} size={18} color={colors.textSecondary} />
      </Pressable>
      {open ? (
        <View
          style={[
            styles.menu,
            {
              backgroundColor: colors.surface,
              borderColor: colors.border,
            },
          ]}
        >
          {searchable ? (
            <TextInput
              value={query}
              onChangeText={setQuery}
              placeholder={searchPlaceholder}
              placeholderTextColor={colors.textMuted}
              style={[
                styles.search,
                {
                  backgroundColor: colors.inputBackground,
                  borderColor: colors.border,
                  color: colors.text,
                },
              ]}
            />
          ) : null}
          {filtered.map((option) => {
            const isSelected = option.value === value;
            return (
              <Pressable
                key={option.value}
                accessibilityRole="button"
                accessibilityState={{ selected: isSelected }}
                onPress={() => {
                  onChange(option.value);
                  setOpen(false);
                  setQuery('');
                }}
                style={[
                  styles.option,
                  {
                    backgroundColor: isSelected ? colors.controlSelectedBackground : 'transparent',
                    borderColor: isSelected ? colors.controlSelectedBorder : 'transparent',
                  },
                ]}
              >
                <Text
                  variant="body"
                  color={isSelected ? colors.controlSelectedText : colors.text}
                >
                  {option.label}
                </Text>
              </Pressable>
            );
          })}
        </View>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { gap: spacing.sm, marginVertical: spacing.sm },
  trigger: {
    minHeight: 48,
    borderWidth: 1,
    borderRadius: radius.md,
    paddingHorizontal: spacing.lg,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: spacing.sm,
  },
  triggerText: { flex: 1 },
  menu: {
    borderWidth: 1,
    borderRadius: radius.md,
    overflow: 'hidden',
    maxHeight: 280,
  },
  search: {
    margin: spacing.sm,
    borderWidth: 1,
    borderRadius: radius.sm,
    minHeight: 40,
    paddingHorizontal: spacing.md,
  },
  option: {
    minHeight: 44,
    paddingHorizontal: spacing.lg,
    justifyContent: 'center',
    borderWidth: 1,
  },
});
