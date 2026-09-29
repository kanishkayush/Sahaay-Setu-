import { Text as RNText, type TextProps as RNTextProps, StyleSheet } from 'react-native';
import { typography, useTheme } from '@/theme';

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
export function Text({ variant = 'body', color, center, style, ...rest }: TextProps) {
  const { colors } = useTheme();
  return (
    <RNText
      style={[typography[variant] as object, { color: color ?? colors.text }, center && styles.center, style]}
      maxFontSizeMultiplier={1.6}
      {...rest}
    />
  );
}

const styles = StyleSheet.create({ center: { textAlign: 'center' } });
