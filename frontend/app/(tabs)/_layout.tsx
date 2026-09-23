import { StyleSheet, View, Platform } from 'react-native';
import { Tabs } from 'expo-router';
import { useTranslation } from 'react-i18next';
import { BlurView } from 'expo-blur';

import { Icon, type IconName, Text } from '@/components/ui';
import { colors, radius, spacing } from '@/theme';

function TabIcon({ name, focused }: { name: IconName; focused: boolean }) {
  return (
    <View style={[styles.iconWrap, focused && styles.iconWrapActive]}>
      <Icon
        name={name}
        size={23}
        color={focused ? colors.primary : colors.textSecondary}
        strokeWidth={focused ? 2 : 1.7}
      />
    </View>
  );
}

function TabLabel({ children, focused }: { children: string; focused: boolean }) {
  return (
    <Text
      variant="label"
      color={focused ? colors.primary : colors.textSecondary}
      numberOfLines={2}
      style={styles.label}
    >
      {children}
    </Text>
  );
}

export default function TabsLayout() {
  const { t } = useTranslation();

  const tab = (name: IconName) =>
    function TabBarIcon({ focused }: { focused: boolean }) {
      return <TabIcon name={name} focused={focused} />;
    };

  const label = (text: string) =>
    function TabBarLabel({ focused }: { focused: boolean }) {
      return <TabLabel focused={focused}>{text}</TabLabel>;
    };

  return (
    <Tabs
      screenOptions={{
        headerShown: false,
        tabBarActiveTintColor: colors.primary,
        tabBarInactiveTintColor: colors.textSecondary,
        tabBarStyle: styles.bar,
        tabBarItemStyle: styles.item,
        tabBarBackground: () => (
          <BlurView intensity={20} tint="light" style={StyleSheet.absoluteFill} />
        ),
      }}
    >
      <Tabs.Screen
        name="home"
        options={{
          title: t('nav.home'),
          tabBarIcon: tab('home'),
          tabBarLabel: label(t('nav.home')),
        }}
      />
      <Tabs.Screen
        name="schemes"
        options={{
          title: t('nav.schemes'),
          tabBarIcon: tab('list'),
          tabBarLabel: label(t('nav.schemes')),
        }}
      />
      <Tabs.Screen
        name="calculator"
        options={{
          title: t('nav.calculator'),
          tabBarIcon: tab('calc'),
          tabBarLabel: label(t('nav.calculator')),
        }}
      />
      <Tabs.Screen
        name="partners"
        options={{
          title: t('nav.partners'),
          tabBarIcon: tab('pin'),
          tabBarLabel: label(t('nav.partners')),
        }}
      />
      <Tabs.Screen
        name="profile"
        options={{
          title: t('nav.profile'),
          tabBarIcon: tab('user'),
          tabBarLabel: label(t('nav.profile')),
        }}
      />
    </Tabs>
  );
}

const styles = StyleSheet.create({
  bar: {
    backgroundColor: Platform.OS === 'web' ? colors.glassStrong : 'transparent',
    borderTopColor: colors.glassBorder,
    borderTopWidth: 1,
    height: 96,
    paddingTop: spacing.sm,
    paddingBottom: spacing.xl,
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    elevation: 0, // Remove shadow on Android for absolute bar
  },
  label: { textAlign: 'center', lineHeight: 16, marginTop: 3, paddingHorizontal: 2 },
  item: { paddingVertical: 2 },
  iconWrap: {
    minWidth: 56,
    height: 30,
    borderRadius: radius.pill,
    alignItems: 'center',
    justifyContent: 'center',
  },
  iconWrapActive: { backgroundColor: colors.primarySurface },
});
