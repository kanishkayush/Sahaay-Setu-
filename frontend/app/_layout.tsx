import { useEffect, useState } from 'react';
import { ActivityIndicator, View } from 'react-native';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Stack } from 'expo-router';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { StatusBar } from 'expo-status-bar';
import 'react-native-gesture-handler';

import { initI18n } from '@/i18n';
import { useAppStore } from '@/store/useAppStore';
import { ThemeProvider, hydrateThemePreference, useTheme } from '@/theme';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
      staleTime: 1000 * 60 * 5,
    },
  },
});

function ThemedStack() {
  const { colors, mode } = useTheme();
  return (
    <>
      <StatusBar style={mode === 'dark' ? 'light' : 'dark'} />
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
    </>
  );
}

export default function RootLayout() {
  const [ready, setReady] = useState(false);
  const [initialMode, setInitialMode] = useState<'light' | 'dark'>('light');
  const [initialPreference, setInitialPreference] = useState<'light' | 'dark' | null>(null);
  const setLanguageState = useAppStore((s) => s.setLanguage);

  useEffect(() => {
    let cancelled = false;
    Promise.all([
      initI18n().then((language) => {
        if (!cancelled) void setLanguageState(language);
      }).catch(() => {}),
      hydrateThemePreference(),
    ])
      .then(([, theme]) => {
        if (cancelled) return;
        setInitialMode(theme.mode);
        setInitialPreference(theme.preference);
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
          backgroundColor: initialMode === 'dark' ? '#0B1220' : '#F4FAFF',
        }}
      >
        <ActivityIndicator size="large" color={initialMode === 'dark' ? '#4C8DFF' : '#0757D9'} />
      </View>
    );
  }

  return (
    <SafeAreaProvider>
      <QueryClientProvider client={queryClient}>
        <ThemeProvider initialMode={initialMode} initialPreference={initialPreference}>
          <ThemedStack />
        </ThemeProvider>
      </QueryClientProvider>
    </SafeAreaProvider>
  );
}
