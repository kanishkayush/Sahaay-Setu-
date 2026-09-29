import { View } from 'react-native';
import { useTranslation } from 'react-i18next';

import { SegmentedControl } from './SegmentedControl';
import { Text } from './Text';
import { spacing, useTheme, type ThemeMode } from '@/theme';

export function ThemeToggle() {
  const { t } = useTranslation();
  const { mode, setPreference } = useTheme();

  return (
    <View style={{ gap: spacing.sm }}>
      <Text variant="subheading">{t('profile.appearance')}</Text>
      <Text variant="caption">
        {mode === 'dark' ? t('profile.themeDarkActive') : t('profile.themeLightActive')}
      </Text>
      <SegmentedControl
        segments={[
          { value: 'light', label: t('profile.themeLight') },
          { value: 'dark', label: t('profile.themeDark') },
        ]}
        value={mode}
        onChange={(value) => {
          void setPreference(value as ThemeMode);
        }}
      />
    </View>
  );
}
