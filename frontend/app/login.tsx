import React, { useState } from 'react';
import { View, StyleSheet, TextInput, KeyboardAvoidingView, Platform, ScrollView } from 'react-native';
import { router } from 'expo-router';
import { LinearGradient } from 'expo-linear-gradient';
import { Button, Text, Card } from '@/components/ui';
import { useTranslation } from 'react-i18next';
import { spacing, typography, useTheme } from '@/theme';
import { useAppStore } from '@/store/useAppStore';
import { login } from '@/api/services/auth.service';
import { normalizeIndianMobile } from '@/auth/indianMobile';

export default function LoginScreen() {
  const { t } = useTranslation();
  const { colors } = useTheme();
  const setAuthStatus = useAppStore((s) => s.setAuthStatus);
  const [inputValue, setInputValue] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  const normalized = normalizeIndianMobile(inputValue);
  const canSubmit = Boolean(normalized);

  const handleLogin = async () => {
    setErrorMsg('');
    const phone = normalizeIndianMobile(inputValue);
    if (!phone) {
      setErrorMsg('Enter a valid 10-digit Indian mobile number starting with 6, 7, 8 or 9');
      return;
    }
    
    setIsSubmitting(true);
    try {
      const res = await login(phone);
      setAuthStatus('authenticated', res.token);
      router.replace('/(tabs)/home');
    } catch (e: any) {
      setErrorMsg(e.message || 'Error logging in');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <KeyboardAvoidingView 
      style={styles.container} 
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
    >
      <LinearGradient
        colors={[...colors.gradient]}
        start={{ x: 0, y: 0 }}
        end={{ x: 1, y: 1 }}
        style={StyleSheet.absoluteFill}
      />
      <ScrollView contentContainerStyle={styles.scrollContent} keyboardShouldPersistTaps="handled">
        <View style={styles.brandingContainer}>
          <Text variant="title" style={[styles.title, { color: colors.primaryDark }]}>{t('login.title')}</Text>
          <Text variant="body" color={colors.textSecondary} style={styles.subtitle}>
            {t('login.subtitle')}
          </Text>
        </View>

        <Card variant="glass" padded={false} style={styles.formContainer}>
          <>
            <Text variant="bodyStrong" style={[styles.label, { color: colors.text }]}>
              {t('login.loginOrRegister', 'Login or Register')}
            </Text>
            <TextInput
              style={[
                styles.input,
                {
                  backgroundColor: colors.inputBackground,
                  borderColor: colors.border,
                  color: colors.text,
                },
              ]}
              placeholder={t('login.placeholder', 'Mobile number (e.g. 9876543210)')}
              placeholderTextColor={colors.textMuted}
              value={inputValue}
              onChangeText={(text) => {
                setInputValue(text);
                setErrorMsg('');
              }}
              keyboardType="phone-pad"
              autoCapitalize="none"
              autoComplete="tel"
            />
            
            {errorMsg ? <Text variant="caption" color={colors.danger} style={{marginBottom: spacing.md}}>{errorMsg}</Text> : null}
            
            <Button 
              title={isSubmitting ? t('login.pleaseWait', 'Please wait...') : t('common.login', 'LOGIN')}
              onPress={handleLogin}
              disabled={!canSubmit || isSubmitting}
              style={styles.button}
            />
          </>
          
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
  },
  input: {
    ...typography.body,
    borderWidth: 1,
    borderRadius: 14,
    paddingHorizontal: spacing.lg,
    minHeight: 52,
    marginBottom: spacing.xxl,
  },
  button: {
    marginBottom: spacing.lg,
  },
  disclaimer: {
    paddingHorizontal: spacing.sm,
  }
});
