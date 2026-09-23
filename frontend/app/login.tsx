import React, { useState } from 'react';
import { View, StyleSheet, TextInput, KeyboardAvoidingView, Platform, ScrollView } from 'react-native';
import { router } from 'expo-router';
import { LinearGradient } from 'expo-linear-gradient';
import { Button, Text, Card } from '@/components/ui';
import { useTranslation } from 'react-i18next';
import { colors, radius, spacing, typography } from '@/theme';
import { useAppStore } from '@/store/useAppStore';

export default function LoginScreen() {
  const { t } = useTranslation();
  const setAuthStatus = useAppStore((s) => s.setAuthStatus);
  const [inputValue, setInputValue] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const finishLogin = () => {
    setAuthStatus('authenticated');
    router.replace('/(tabs)/home');
  };

  const handleContinue = () => {
    setIsSubmitting(true);
    setTimeout(() => {
      setIsSubmitting(false);
      finishLogin();
    }, 600);
  };

  return (
    <KeyboardAvoidingView 
      style={styles.container} 
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
    >
      <LinearGradient
        colors={['#F4FAFF', '#EAF6FF', '#F8FCFF']}
        start={{ x: 0, y: 0 }}
        end={{ x: 1, y: 1 }}
        style={StyleSheet.absoluteFill}
      />
      <ScrollView contentContainerStyle={styles.scrollContent} keyboardShouldPersistTaps="handled">
        <View style={styles.brandingContainer}>
          <Text variant="title" style={styles.title}>{t('login.title')}</Text>
          <Text variant="body" color={colors.textSecondary} style={styles.subtitle}>
            {t('login.subtitle')}
          </Text>
        </View>

        <Card variant="glass" padded={false} style={styles.formContainer}>
          <Text variant="bodyStrong" style={styles.label}>
            {t('login.loginOrRegister')}
          </Text>
          <TextInput
            style={styles.input}
            placeholder={t('login.placeholder')}
            placeholderTextColor={colors.textSecondary}
            value={inputValue}
            onChangeText={setInputValue}
            keyboardType="default"
            autoCapitalize="none"
            autoComplete="off"
          />
          
          <Button 
            title={isSubmitting ? t('login.pleaseWait') : t('common.continue')}
            onPress={handleContinue}
            disabled={inputValue.trim().length < 4 || isSubmitting}
            style={styles.button}
          />
          
          <Text variant="caption" color={colors.textSecondary} center style={styles.disclaimer}>
            {t('login.disclaimer')}
          </Text>
        </Card>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  scrollContent: {
    flexGrow: 1,
    justifyContent: 'center',
    padding: spacing.xl,
  },
  brandingContainer: {
    alignItems: 'center',
    marginBottom: spacing.xxxl * 1.5,
  },
  title: {
    fontSize: 32,
    color: colors.primaryDark,
    textAlign: 'center',
    marginBottom: spacing.md,
    lineHeight: 40,
  },
  subtitle: {
    textAlign: 'center',
    lineHeight: 24,
  },
  formContainer: {
    padding: spacing.xl,
  },
  label: {
    marginBottom: spacing.lg,
    color: colors.text,
  },
  input: {
    ...typography.body,
    backgroundColor: colors.glassInput,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 14,
    paddingHorizontal: spacing.lg,
    minHeight: 52,
    marginBottom: spacing.xxl,
    color: colors.text,
  },
  button: {
    marginBottom: spacing.lg,
  },
  disclaimer: {
    paddingHorizontal: spacing.sm,
  }
});
