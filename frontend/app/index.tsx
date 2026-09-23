import { useEffect } from 'react';
import { ActivityIndicator, View } from 'react-native';
import { router } from 'expo-router';
import { useAppStore } from '@/store/useAppStore';
import { colors } from '@/theme';

/**
 * Entry gate. Sends first-time users through language selection, and everyone
 * else straight to the tabs.
 */
export default function Index() {
  const hasCompletedOnboarding = useAppStore((s) => s.hasCompletedOnboarding);

  useEffect(() => {
    // Defer a tick so the root navigator is mounted before we redirect.
    const id = setTimeout(() => {
      router.replace(hasCompletedOnboarding ? '/login' : '/onboarding/language');
    }, 0);
    return () => clearTimeout(id);
  }, [hasCompletedOnboarding]);

  return (
    <View
      style={{
        flex: 1,
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: colors.background,
      }}
    >
      <ActivityIndicator size="large" color={colors.primary} />
    </View>
  );
}
