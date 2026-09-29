import {
  ActivityIndicator,
  Pressable,
  StyleSheet,
  View,
  type PressableProps,
  type ViewStyle,
} from 'react-native';
import * as Haptics from 'expo-haptics';
import { Text } from './Text';
import { radius, spacing, shadow, MIN_TOUCH_SIZE, useTheme, type ColorTokens } from '@/theme';

type Variant = 'primary' | 'secondary' | 'outline' | 'ghost' | 'danger';
type Size = 'sm' | 'md' | 'lg';

export type ButtonProps = Omit<PressableProps, 'style'> & {
  title: string;
  variant?: Variant;
  size?: Size;
  loading?: boolean;
  fullWidth?: boolean;
  icon?: React.ReactNode;
  style?: ViewStyle;
};

function variantStyle(variant: Variant, colors: ColorTokens): ViewStyle {
  switch (variant) {
    case 'primary':
      return { backgroundColor: colors.primary, ...shadow.glass };
    case 'secondary':
      return {
        backgroundColor: colors.glassInput,
        borderWidth: 1,
        borderColor: colors.border,
      };
    case 'outline':
      return { backgroundColor: 'transparent', borderWidth: 1.5, borderColor: colors.primary };
    case 'ghost':
      return { backgroundColor: 'transparent' };
    case 'danger':
      return { backgroundColor: colors.dangerText };
    default:
      return {};
  }
}

function variantText(variant: Variant, colors: ColorTokens): string {
  switch (variant) {
    case 'primary':
      return colors.primaryText;
    case 'secondary':
    case 'outline':
    case 'ghost':
      return colors.primary;
    case 'danger':
      return colors.textInverse;
    default:
      return colors.text;
  }
}

export function Button({
  title,
  variant = 'primary',
  size = 'md',
  loading = false,
  fullWidth = true,
  disabled,
  icon,
  style,
  onPress,
  ...rest
}: ButtonProps) {
  const { colors } = useTheme();
  const isDisabled = disabled || loading;
  const fg = variantText(variant, colors);

  return (
    <Pressable
      accessibilityRole="button"
      accessibilityState={{ disabled: isDisabled, busy: loading }}
      accessibilityLabel={title}
      disabled={isDisabled}
      onPress={(event) => {
        Haptics.selectionAsync().catch(() => {});
        onPress?.(event);
      }}
      style={({ pressed }) => [
        styles.base,
        sizeStyles[size],
        variantStyle(variant, colors),
        fullWidth && styles.fullWidth,
        pressed && !isDisabled && styles.pressed,
        isDisabled && styles.disabled,
        style,
      ]}
      {...rest}
    >
      {loading ? (
        <ActivityIndicator color={fg} />
      ) : (
        <View style={styles.content}>
          {icon}
          <Text
            variant={size === 'lg' ? 'subheading' : 'bodyStrong'}
            color={fg}
            style={styles.label}
          >
            {title}
          </Text>
        </View>
      )}
    </Pressable>
  );
}

const styles = StyleSheet.create({
  base: {
    minHeight: MIN_TOUCH_SIZE,
    borderRadius: radius.pill,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: spacing.lg,
  },
  fullWidth: { alignSelf: 'stretch' },
  content: { flexDirection: 'row', alignItems: 'center', gap: spacing.sm },
  label: { textAlign: 'center' },
  pressed: { opacity: 0.85, transform: [{ scale: 0.99 }] },
  disabled: { opacity: 0.45 },
});

const sizeStyles: Record<Size, ViewStyle> = {
  sm: { minHeight: MIN_TOUCH_SIZE, paddingVertical: spacing.sm },
  md: { minHeight: 52, paddingVertical: spacing.md },
  lg: { minHeight: 58, paddingVertical: spacing.lg },
};
