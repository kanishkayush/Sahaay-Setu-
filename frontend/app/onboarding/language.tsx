import { useState } from 'react';
import { Pressable, StyleSheet, View } from 'react-native';
import { router } from 'expo-router';
import { useTranslation } from 'react-i18next';

import type { LanguageCode } from '@/api/contracts';
import { Button, Screen, Text } from '@/components/ui';
import { SUPPORTED_LANGUAGES } from '@/i18n';
import { useAppStore } from '@/store/useAppStore';
import { colors, radius, spacing, MIN_TOUCH_SIZE } from '@/theme';

/**
 * The first screen anyone sees.
 *
 * Every option is written in its own script (the endonym), never translated —
 * a user who cannot read English must still be able to find their language.
 * Selecting one switches the UI immediately so they get instant confirmation.
 */
export default function LanguageScreen() {
  const { t } = useTranslation();
  const language = useAppStore((s) => s.language);
  const setLanguage = useAppStore((s) => s.setLanguage);
  const [pending, setPending] = useState<LanguageCode | null>(null);

  const select = async (code: LanguageCode) => {
    setPending(code);
    await setLanguage(code);
    setPending(null);
  };

  return (
    <Screen
      edges={['top', 'bottom']}
      footer={
        <Button title={t('common.continue')} onPress={() => router.push('/onboarding/intro')} />
      }
    >
      <View style={styles.header}>
        <Text variant="display">{t('common.appName')}</Text>
        <Text variant="body" color={colors.textSecondary}>
          {t('common.tagline')}
        </Text>
      </View>

      <View style={styles.titleBlock}>
        <Text variant="heading">{t('language.title')}</Text>
        <Text variant="caption" color={colors.textMuted}>
          {t('language.subtitle')}
        </Text>
      </View>

      <View style={styles.grid}>
        {SUPPORTED_LANGUAGES.map((option) => {
          const selected = option.code === language;
          return (
            <Pressable
              key={option.code}
              accessibilityRole="radio"
              accessibilityState={{ selected }}
              accessibilityLabel={`${option.endonym} — ${option.englishName}`}
              onPress={() => select(option.code)}
              style={({ pressed }) => [
                styles.card,
                selected && styles.cardSelected,
                pressed && styles.pressed,
                pending === option.code && styles.pending,
              ]}
            >
              <Text variant="heading" color={selected ? colors.primary : colors.text}>
                {option.endonym}
              </Text>
              <Text variant="caption" color={colors.textMuted}>
                {option.englishName}
              </Text>
            </Pressable>
          );
        })}
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({
  header: { gap: spacing.xs, marginTop: spacing.xxl },
  titleBlock: { gap: spacing.xs, marginTop: spacing.lg },
  grid: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing.md },
  card: {
    flexBasis: '47%',
    flexGrow: 1,
    minHeight: MIN_TOUCH_SIZE + 36,
    gap: 2,
    padding: spacing.lg,
    backgroundColor: colors.surface,
    borderWidth: 2,
    borderColor: colors.border,
    borderRadius: radius.lg,
  },
  cardSelected: { borderColor: colors.primary, backgroundColor: colors.primarySurface },
  pressed: { opacity: 0.85 },
  pending: { opacity: 0.6 },
});
