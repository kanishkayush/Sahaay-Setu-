import { StyleSheet, View, Platform, useWindowDimensions } from 'react-native';
import { Tabs } from 'expo-router';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useTranslation } from 'react-i18next';
import { BlurView } from 'expo-blur';

import { Icon, type IconName, Text } from '@/components/ui';
import { radius, spacing, useTheme } from '@/theme';

function TabIcon({ name, focused }: { name: IconName; focused: boolean }) {
  const { colors } = useTheme();
  return (
    <View style={[styles.iconWrap, focused && { backgroundColor: colors.navSelectedBackground }]}>
      <Icon
        name={name}
        size={23}
        color={focused ? colors.navSelectedForeground : colors.textSecondary}
        strokeWidth={focused ? 2 : 1.7}
      />
    </View>
  );
}

function TabLabel({ children, focused }: { children: string; focused: boolean }) {
  const { colors } = useTheme();
  return (
    <Text
      variant="label"
      color={focused ? colors.navSelectedForeground : colors.textSecondary}
      numberOfLines={2}
      style={styles.label}
    >
      {children}
    </Text>
  );
}

export default function TabsLayout() {
  const { t } = useTranslation();
  const { colors, mode } = useTheme();
  const insets = useSafeAreaInsets();
  const { width } = useWindowDimensions();
  const barHeight = 60 + insets.bottom;
  const tabWidth = width / 5;

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
        tabBarActiveTintColor: colors.navSelectedForeground,
        tabBarInactiveTintColor: colors.textSecondary,
        tabBarStyle: [
          styles.bar,
          {
            height: barHeight,
            paddingBottom: insets.bottom + spacing.xs,
            backgroundColor: Platform.OS === 'web' ? colors.glassStrong : 'transparent',
            borderTopColor: colors.glassBorder,
          },
        ],
        tabBarItemStyle: [styles.item, { width: tabWidth }],
        tabBarBackground: () => (
          <BlurView intensity={30} tint={mode === 'dark' ? 'dark' : 'light'} style={StyleSheet.absoluteFill} />
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
    borderTopWidth: 1,
    position: 'absolute',
    bottom: 0,
    left: 0,
    right: 0,
    elevation: 0,
  },
  label: {
    textAlign: 'center',
    lineHeight: 14,
    marginTop: 2,
    paddingHorizontal: 2,
  },
  item: {
    paddingVertical: 0,
    alignItems: 'center',
    justifyContent: 'flex-start',
  },
  iconWrap: {
    width: 56,
    height: 32,
    borderRadius: radius.pill,
    alignItems: 'center',
    justifyContent: 'center',
  },
});
