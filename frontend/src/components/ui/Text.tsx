import { Text as RNText, type TextProps as RNTextProps, StyleSheet } from 'react-native';
import { colors, typography } from '@/theme';

type Variant = keyof typeof typography;

export type TextProps = RNTextProps & {
  variant?: Variant;
  color?: string;
  center?: boolean;
};

/**
 * The only Text component in the app. Using it everywhere guarantees Indic
 * scripts get the roomier line heights defined in the theme.
 */
export function Text({ variant = 'body', color = colors.text, center, style, ...rest }: TextProps) {
  return (
    <RNText
      style={[typography[variant] as object, { color }, center && styles.center, style]}
      // Respect the OS font-size setting, but cap it so layouts don't shatter.
      maxFontSizeMultiplier={1.6}
      {...rest}
    />
  );
}

const styles = StyleSheet.create({ center: { textAlign: 'center' } });
