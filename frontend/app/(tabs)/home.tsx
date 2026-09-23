// @ts-nocheck
import React from 'react';
import { StyleSheet, View, TextInput, Pressable } from 'react-native';
import { router } from 'expo-router';
import { useTranslation } from 'react-i18next';

import { Screen, Text, Icon, Card } from '@/components/ui';
import { USE_MOCK_API } from '@/api/config';
import { useSchemes } from '@/hooks/useSchemes';
import { colors, spacing, radius, typography } from '@/theme';

export default function HomeScreen() {
  const { t } = useTranslation();

  return (
    <Screen>
      <View style={styles.topNav}>
        <Text variant="title" style={styles.navTitle}>{t('common.appName')}</Text>
        <View style={styles.navActions}>
          <Pressable style={styles.iconBtn}>
            <Icon name="bell" size={24} color={colors.primary} />
          </Pressable>
          <Pressable style={styles.avatarBtn} onPress={() => router.push('/(tabs)/profile')}>
            <Text style={styles.avatarText}>SP</Text>
          </Pressable>
        </View>
      </View>

      {/* Greeting & Header */}
      <View style={styles.header}>
        <Text variant="subheading" color={colors.textSecondary}>{t('home.greetingMorning', 'Good morning,')}</Text>
        <Text variant="display" style={styles.mainHeading}>
          {t('home.mainHeading', "Let's build a\nbrighter future together")}
        </Text>
        <Text variant="body" color={colors.textSecondary} style={styles.subtitle}>
          {t('home.mainSubtitle', 'Find financial assistance, schemes, and trusted partners — all in one place.')}
        </Text>
      </View>

      {/* Search Field */}
      <View style={styles.searchContainer}>
        <Icon name="search" size={20} color={colors.textMuted} style={styles.searchIcon} />
        <TextInput
          style={styles.searchInput}
          placeholder={t('home.searchPlaceholder', 'Search schemes, support, or partners...')}
          placeholderTextColor={colors.textSecondary}
        />
      </View>

      {/* Quick Actions */}
      <View style={styles.section}>
        <Text variant="label" color={colors.textSecondary} style={styles.sectionLabel}>
          {t('home.quickActions', 'QUICK ACTIONS')}
        </Text>
        <View style={styles.grid}>
          <ActionCard 
            icon="mic" 
            title={t('home.voiceAssistant', 'Voice Assistant')} 
            onPress={() => router.push('/voice')} 
          />
          <ActionCard 
            icon="target" 
            title={t('home.checkEligibility', 'Check Eligibility')} 
            onPress={() => router.push('/recommend')} 
          />
          <ActionCard 
            icon="list" 
            title={t('home.exploreSchemes', 'Explore Schemes')} 
            onPress={() => router.push('/(tabs)/schemes')} 
          />
          <ActionCard 
            icon="pin" 
            title={t('home.findPartner', 'Find a Partner')} 
            onPress={() => router.push('/(tabs)/partners')} 
          />
          <ActionCard 
            icon="document" 
            title={t('home.documents', 'Documents')} 
            onPress={() => router.push('/(tabs)/profile')} 
          />
          <ActionCard 
            icon="calc" 
            title={t('home.emiCalculator', 'EMI Calculator')} 
            onPress={() => router.push('/(tabs)/calculator')} 
          />
          <ActionCard 
            icon="user" 
            title={t('home.myProfile', 'My Profile')} 
            onPress={() => router.push('/(tabs)/profile')} 
          />
        </View>
      </View>
    </Screen>
  );
}

function ActionCard({ icon, title, onPress }) {
  return (
    <Card variant="glass" padded={false} onPress={onPress} style={styles.actionCard}>
      <View style={styles.actionIconWrap}>
        <Icon name={icon} size={24} color={colors.primary} />
      </View>
      <Text variant="bodyStrong" style={styles.actionTitle} color={colors.text}>
        {title}
      </Text>
    </Card>
  );
}

const styles = StyleSheet.create({
  topNav: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: spacing.sm,
    marginBottom: spacing.md,
  },
  navTitle: {
    color: colors.primaryDark,
    fontSize: 22,
  },
  navActions: {
    flexDirection: 'row',
    gap: spacing.md,
    alignItems: 'center',
  },
  iconBtn: {
    padding: spacing.xs,
  },
  avatarBtn: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: colors.primary,
    alignItems: 'center',
    justifyContent: 'center',
  },
  avatarText: {
    color: colors.surface,
    fontWeight: '700',
    fontSize: 14,
  },
  header: {
    gap: spacing.sm,
    marginBottom: spacing.xl,
  },
  mainHeading: {
    color: colors.primaryDark,
    lineHeight: 38,
  },
  subtitle: {
    lineHeight: 24,
    marginTop: spacing.xs,
  },
  searchContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: colors.glassInput,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 16,
    paddingHorizontal: spacing.md,
    height: 52,
    marginBottom: spacing.xxl,
  },
  searchIcon: {
    marginRight: spacing.sm,
  },
  searchInput: {
    flex: 1,
    ...typography.body,
    color: colors.text,
  },
  section: {
    gap: spacing.md,
    marginBottom: spacing.xxxl,
  },
  sectionLabel: {
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  grid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing.md,
  },
  actionCard: {
    width: '47%',
    padding: spacing.lg,
    gap: spacing.md,
    alignItems: 'flex-start',
  },
  actionIconWrap: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: colors.primarySurface,
    alignItems: 'center',
    justifyContent: 'center',
  },
  actionTitle: {
    lineHeight: 22,
  },
});
