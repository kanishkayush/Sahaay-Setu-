import { BlurView } from 'expo-blur';
import { Platform, Pressable, StyleSheet, View, type StyleProp, type ViewProps, type ViewStyle } from 'react-native';
import { colors, radius, shadow, spacing } from '@/theme';

export type CardProps = ViewProps & {
  onPress?: () => void;
  padded?: boolean;
  /** Use 'glass' for translucent cards, 'solid' for form containers */
  variant?: 'solid' | 'glass';
  accessibilityLabel?: string;
  style?: StyleProp<ViewStyle>;
};

/**
 * Layout vs shadow style splitter for the glass variant.
 *
 * Root cause of Issue 2 (icon misalignment):
 *   Previously `style` went to the outer shadow-bearing wrapper only. But
 *   padding, gap, and alignItems had zero effect there — the BlurView inside
 *   was 100% fill and children had no layout constraints applied to them.
 *
 * Fix: split the style prop:
 *   - OUTER_PROPS (width, flex, margin, position) → outer shadow wrapper
 *   - Everything else (padding, gap, alignItems, etc.) → content layer View
 */
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
  const isGlass = variant === 'glass';

  let content;

  if (isGlass) {
    const { outer, inner } = splitStyle(style);
    content = (
      <View style={[styles.glassShadow, outer]} {...rest}>
        {/* Frosted blur layer fills the outer wrapper */}
        <BlurView
          intensity={Platform.OS === 'web' ? 0 : 20}
          tint="light"
          style={StyleSheet.absoluteFill}
        />
        {/* Solid glass tint — visible on web where BlurView is no-op */}
        <View style={[styles.glassOverlay, StyleSheet.absoluteFill]} pointerEvents="none" />
        {/* Content layer: layout/spacing props reach children here */}
        <View style={[styles.contentLayer, padded && styles.padded, inner]}>
          {children}
        </View>
      </View>
    );
  } else {
    content = (
      <View style={[styles.card, padded && styles.padded, style]} {...rest}>
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
    backgroundColor: colors.surface,
    borderRadius: radius.lg,
    borderWidth: 1,
    borderColor: colors.border,
    ...shadow.card,
  },
  glassShadow: {
    borderRadius: radius.lg,
    overflow: 'hidden',
    borderWidth: 1,
    borderColor: colors.glassBorder,
    ...shadow.glass,
  },
  glassOverlay: {
    backgroundColor: colors.glass,
    borderRadius: radius.lg,
  },
  /** Normal flex container that sits on top of the blur layer */
  contentLayer: {
    flexDirection: 'column',
  },
  padded: { padding: spacing.lg },
  pressed: { opacity: 0.9, transform: [{ scale: 0.995 }] },
});
