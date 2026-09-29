import { BlurView } from 'expo-blur';
import { Platform, Pressable, StyleSheet, View, type StyleProp, type ViewProps, type ViewStyle } from 'react-native';
import { radius, shadow, spacing, useTheme } from '@/theme';

export type CardProps = ViewProps & {
  onPress?: () => void;
  padded?: boolean;
  /** Use 'glass' for translucent cards, 'solid' for form containers */
  variant?: 'solid' | 'glass';
  accessibilityLabel?: string;
  style?: StyleProp<ViewStyle>;
};

const OUTER_PROPS = new Set([
  'width', 'height', 'minWidth', 'maxWidth', 'minHeight', 'maxHeight',
  'flex', 'flexGrow', 'flexShrink', 'flexBasis', 'alignSelf',
  'position', 'top', 'bottom', 'left', 'right',
  'margin', 'marginTop', 'marginBottom', 'marginLeft', 'marginRight',
  'marginHorizontal', 'marginVertical', 'marginStart', 'marginEnd',
]);

function splitStyle(style: StyleProp<ViewStyle>): { outer: ViewStyle; inner: ViewStyle } {
  const flat = StyleSheet.flatten(style) ?? {};
  const outer: Record<string, unknown> = {};
  const inner: Record<string, unknown> = {};
  for (const [key, val] of Object.entries(flat)) {
    if (OUTER_PROPS.has(key)) {
      outer[key] = val;
    } else {
      inner[key] = val;
    }
  }
  return { outer: outer as ViewStyle, inner: inner as ViewStyle };
}

export function Card({
  onPress,
  padded = true,
  variant = 'solid',
  style,
  children,
  ...rest
}: CardProps) {
  const { colors, mode } = useTheme();
  const isGlass = variant === 'glass';

  let content;

  if (isGlass) {
    const { outer, inner } = splitStyle(style);
    content = (
      <View
        style={[
          styles.glassShadow,
          { borderColor: colors.glassBorder },
          outer,
        ]}
        {...rest}
      >
        <BlurView
          intensity={Platform.OS === 'web' ? 0 : 20}
          tint={mode === 'dark' ? 'dark' : 'light'}
          style={StyleSheet.absoluteFill}
        />
        <View
          style={[styles.glassOverlay, StyleSheet.absoluteFill, { backgroundColor: colors.glass }]}
          pointerEvents="none"
        />
        <View style={[styles.contentLayer, padded && styles.padded, inner]}>
          {children}
        </View>
      </View>
    );
  } else {
    content = (
      <View
        style={[
          styles.card,
          {
            backgroundColor: colors.surface,
            borderColor: colors.border,
          },
          padded && styles.padded,
          style,
        ]}
        {...rest}
      >
        {children}
      </View>
    );
  }

  if (!onPress) return content;

  return (
    <Pressable
      accessibilityRole="button"
      onPress={onPress}
      style={({ pressed }) => (pressed ? styles.pressed : undefined)}
    >
      {content}
    </Pressable>
  );
}

const styles = StyleSheet.create({
  card: {
    borderRadius: radius.lg,
    borderWidth: 1,
    ...shadow.card,
  },
  glassShadow: {
    borderRadius: radius.lg,
    overflow: 'hidden',
    borderWidth: 1,
    ...shadow.glass,
  },
  glassOverlay: {
    borderRadius: radius.lg,
  },
  contentLayer: {
    flexDirection: 'column',
  },
  padded: { padding: spacing.lg },
  pressed: { opacity: 0.9, transform: [{ scale: 0.995 }] },
});
