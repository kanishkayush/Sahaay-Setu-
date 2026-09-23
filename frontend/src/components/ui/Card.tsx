import { BlurView } from 'expo-blur';
import { Pressable, StyleSheet, View, type ViewProps, type ViewStyle } from 'react-native';
import { colors, radius, shadow, spacing } from '@/theme';

export type CardProps = ViewProps & {
  onPress?: () => void;
  padded?: boolean;
  /** Use 'glass' for translucent cards, 'solid' for form containers */
  variant?: 'solid' | 'glass';
  accessibilityLabel?: string;
  style?: ViewStyle | ViewStyle[];
};

export function Card({ onPress, padded = true, variant = 'solid', style, children, ...rest }: CardProps) {
  const isGlass = variant === 'glass';

  const content = isGlass ? (
    <View style={[styles.glassShadow, style]} {...rest}>
      <BlurView intensity={20} tint="light" style={[styles.glassContainer, padded && styles.padded]}>
        {children}
      </BlurView>
    </View>
  ) : (
    <View style={[styles.card, padded && styles.padded, style]} {...rest}>
      {children}
    </View>
  );

  if (!onPress) return content;

  return (
    <Pressable
      accessibilityRole="button"
      onPress={onPress}
      style={({ pressed }) => pressed && styles.pressed}
    >
      {content}
    </Pressable>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: colors.surface,
    borderRadius: radius.lg,
    borderWidth: 1,
    borderColor: colors.border,
    ...shadow.card,
  },
  glassShadow: {
    borderRadius: radius.lg,
    ...shadow.glass,
  },
  glassContainer: {
    backgroundColor: colors.glass,
    borderRadius: radius.lg,
    borderWidth: 1,
    borderColor: colors.glassBorder,
    overflow: 'hidden',
  },
  padded: { padding: spacing.lg },
  pressed: { opacity: 0.9, transform: [{ scale: 0.995 }] },
});
