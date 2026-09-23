import { useEffect, useState } from 'react';
import { ActivityIndicator, View } from 'react-native';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Stack } from 'expo-router';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { StatusBar } from 'expo-status-bar';
import 'react-native-gesture-handler';

import { initI18n } from '@/i18n';
import { useAppStore } from '@/store/useAppStore';
import { colors } from '@/theme';

/**
 * Root layout.
 *
 * Boot order matters: i18n must finish before the first screen paints, or the
 * user briefly sees English before their language loads — a jarring first
 * impression in an app whose whole point is speaking their language.
 */

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
      staleTime: 1000 * 60 * 5,
    },
  },
});

export default function RootLayout() {
  const [ready, setReady] = useState(false);
  const setLanguageState = useAppStore((s) => s.setLanguage);

  useEffect(() => {
    let cancelled = false;
    initI18n()
      .then((language) => {
        if (cancelled) return;
        // Keep the store in step with whatever i18n resolved (stored or device).
        void setLanguageState(language);
      })
      .catch(() => {
        // Never block the app on an i18n failure — English is already bundled.
      })
      .finally(() => {
        if (!cancelled) setReady(true);
      });
    return () => {
      cancelled = true;
    };
  }, [setLanguageState]);

  if (!ready) {
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

  return (
    <SafeAreaProvider>
      <QueryClientProvider client={queryClient}>
        <StatusBar style="dark" />
        <Stack
          screenOptions={{
            headerStyle: { backgroundColor: colors.surface },
            headerTitleStyle: { color: colors.text, fontSize: 18, fontWeight: '600' },
            headerTintColor: colors.primary,
            contentStyle: { backgroundColor: colors.background },
          }}
        >
          <Stack.Screen name="index" options={{ headerShown: false }} />
          <Stack.Screen name="onboarding/language" options={{ headerShown: false }} />
          <Stack.Screen name="onboarding/intro" options={{ headerShown: false }} />
          <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
          <Stack.Screen name="recommend/index" options={{ title: '' }} />
          <Stack.Screen name="recommend/results" options={{ title: '' }} />
          <Stack.Screen name="scheme/[id]" options={{ title: '' }} />
          <Stack.Screen name="partner/[id]" options={{ title: '' }} />
          <Stack.Screen name="assistant" options={{ title: '' }} />
          <Stack.Screen name="voice" options={{ title: '' }} />
        </Stack>
      </QueryClientProvider>
    </SafeAreaProvider>
  );
}
