import { useState } from 'react';
import { StyleSheet, View } from 'react-native';
import { router } from 'expo-router';
import { useTranslation } from 'react-i18next';

import { Button, Icon, Screen, Text } from '@/components/ui';
import { useAppStore } from '@/store/useAppStore';
import { colors, radius, spacing } from '@/theme';

const SLIDES = [
  { icon: 'target', titleKey: 'onboarding.slide1Title', bodyKey: 'onboarding.slide1Body' },
  { icon: 'calc', titleKey: 'onboarding.slide2Title', bodyKey: 'onboarding.slide2Body' },
  { icon: 'pin', titleKey: 'onboarding.slide3Title', bodyKey: 'onboarding.slide3Body' },
] as const;

export default function IntroScreen() {
  const { t } = useTranslation();
  const [index, setIndex] = useState(0);
  const completeOnboarding = useAppStore((s) => s.completeOnboarding);

  const slide = SLIDES[index]!;
  const isLast = index === SLIDES.length - 1;

  const finish = () => {
    completeOnboarding();
    router.replace('/login');
  };

  return (
    <Screen
      edges={['top', 'bottom']}
      footer={
        <View style={styles.footer}>
          <Button
            title={isLast ? t('onboarding.getStarted') : t('common.next')}
            onPress={() => (isLast ? finish() : setIndex((i) => i + 1))}
          />
          <Button title={t('onboarding.skip')} variant="ghost" size="sm" onPress={finish} />
        </View>
      }
    >
      <View style={styles.body}>
        <View style={styles.iconBadge}>
          <Icon name={slide.icon} size={34} color={colors.textInverse} strokeWidth={1.7} />
        </View>
        <Text variant="title" center>
          {t(slide.titleKey)}
        </Text>
        <Text variant="body" color={colors.textSecondary} center>
          {t(slide.bodyKey)}
        </Text>
      </View>

      <View style={styles.dots}>
        {SLIDES.map((s, i) => (
          <View key={s.icon} style={[styles.dot, i === index && styles.dotActive]} />
        ))}
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({
  body: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    gap: spacing.lg,
    marginTop: spacing.xxxl,
  },
  iconBadge: {
    width: 76,
    height: 76,
    borderRadius: radius.lg,
    backgroundColor: colors.inverse,
    alignItems: 'center',
    justifyContent: 'center',
  },
  dots: { flexDirection: 'row', gap: spacing.sm, justifyContent: 'center', marginTop: spacing.xl },
  dot: { width: 8, height: 8, borderRadius: radius.pill, backgroundColor: colors.border },
  dotActive: { width: 24, backgroundColor: colors.primary },
  footer: { gap: spacing.sm },
});
