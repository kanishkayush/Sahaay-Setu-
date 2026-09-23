import { Circle, Path, Rect, Svg } from 'react-native-svg';
import { colors } from '@/theme';

/**
 * Monoline 24x24 icon set, ported from the Open Design system
 * (design/screens/icons.js), which introduced it to replace the emoji the v0
 * app used as functional icons.
 *
 * Emoji were a stopgap: they render inconsistently across Android versions,
 * cannot inherit colour, and carry no semantic meaning. These do all three.
 * Every icon is still paired with a text label - see
 * .agents/skills/sahaay-frontend/references/a11y-touch-and-contrast.md.
 */

type El = { t: string; p: Record<string, string> };

const PATHS: Record<string, El[]> = {
  home: [
    { t: 'path', p: { d: 'M3.6 10.2 12 3.5l8.4 6.7' } },
    { t: 'path', p: { d: 'M5.5 9.1V19a1.5 1.5 0 0 0 1.5 1.5h10a1.5 1.5 0 0 0 1.5-1.5V9.1' } },
    { t: 'path', p: { d: 'M9.8 20.5v-5.3h4.4v5.3' } },
  ],
  list: [
    { t: 'rect', p: { x: '4', y: '3.5', width: '16', height: '17', rx: '2.5' } },
    { t: 'path', p: { d: 'M8 8.5h8M8 12h8M8 15.5h5' } },
  ],
  calc: [
    { t: 'rect', p: { x: '4.5', y: '3', width: '15', height: '18', rx: '2.5' } },
    { t: 'rect', p: { x: '7.5', y: '6', width: '9', height: '4', rx: '1' } },
    {
      t: 'path',
      p: {
        d: 'M8.2 13.5h.01M12 13.5h.01M15.8 13.5h.01M8.2 17h.01M12 17h.01M15.8 17h.01',
        strokeWidth: '2.4',
      },
    },
  ],
  pin: [
    {
      t: 'path',
      p: { d: 'M12 21.2c3.9-4.3 5.9-7.5 5.9-10a5.9 5.9 0 1 0-11.8 0c0 2.5 2 5.7 5.9 10Z' },
    },
    { t: 'circle', p: { cx: '12', cy: '11', r: '2.3' } },
  ],
  user: [
    { t: 'circle', p: { cx: '12', cy: '8', r: '3.6' } },
    { t: 'path', p: { d: 'M4.8 20.4c.7-3.7 3.6-5.8 7.2-5.8s6.5 2.1 7.2 5.8' } },
  ],
  chat: [
    {
      t: 'path',
      p: {
        d: 'M20.5 12c0 4.1-3.8 7.2-8.5 7.2a10 10 0 0 1-2.6-.33L4.6 20.5l1.2-3.5A6.9 6.9 0 0 1 3.5 12c0-4.1 3.8-7.2 8.5-7.2s8.5 3.1 8.5 7.2Z',
      },
    },
    { t: 'path', p: { d: 'M8.6 11.9h.01M12 11.9h.01M15.4 11.9h.01', strokeWidth: '2.4' } },
  ],
  right: [{ t: 'path', p: { d: 'm9.5 5.5 6.5 6.5-6.5 6.5' } }],
  left: [{ t: 'path', p: { d: 'M14.5 5.5 8 12l6.5 6.5' } }],
  down: [{ t: 'path', p: { d: 'm5.5 9.5 6.5 6.5 6.5-6.5' } }],
  up: [{ t: 'path', p: { d: 'm5.5 14.5 6.5-6.5 6.5 6.5' } }],
  check: [{ t: 'path', p: { d: 'm5 12.6 4.6 4.6L19 7.4' } }],
  alert: [
    { t: 'path', p: { d: 'M12 4.6 2.9 20.2h18.2L12 4.6Z' } },
    { t: 'path', p: { d: 'M12 10v4.2' } },
    { t: 'path', p: { d: 'M12 17.3h.01', strokeWidth: '2.4' } },
  ],
  info: [
    { t: 'circle', p: { cx: '12', cy: '12', r: '8.6' } },
    { t: 'path', p: { d: 'M12 11v5.4' } },
    { t: 'path', p: { d: 'M12 7.9h.01', strokeWidth: '2.4' } },
  ],
  phone: [
    {
      t: 'path',
      p: {
        d: 'M8.2 3.9 10 8l-2 1.9a11 11 0 0 0 6.1 6.1L16 14l4.1 1.8-1 3.6a1.6 1.6 0 0 1-1.7 1.2C10.2 20 4 13.8 3.4 6.6A1.6 1.6 0 0 1 4.6 4.9l3.6-1Z',
      },
    },
  ],
  nav: [{ t: 'path', p: { d: 'M20.5 3.5 3.5 10.9l7.3 2.3 2.3 7.3 7.4-17Z' } }],
  search: [
    { t: 'circle', p: { cx: '10.8', cy: '10.8', r: '6.3' } },
    { t: 'path', p: { d: 'm15.4 15.4 4.6 4.6' } },
  ],
  filter: [{ t: 'path', p: { d: 'M4 6.6h16M7 12h10M10 17.4h4' } }],
  close: [{ t: 'path', p: { d: 'm6 6 12 12M18 6 6 18' } }],
  speaker: [
    { t: 'path', p: { d: 'M11.5 4.6 6.9 8.4H3.9v7.2h3l4.6 3.8V4.6Z' } },
    { t: 'path', p: { d: 'M15.2 9.2a4 4 0 0 1 0 5.6M17.9 6.6a7.7 7.7 0 0 1 0 10.8' } },
  ],
  mic: [
    { t: 'rect', p: { x: '9.2', y: '3', width: '5.6', height: '10.6', rx: '2.8' } },
    { t: 'path', p: { d: 'M5.6 11.4a6.4 6.4 0 0 0 12.8 0' } },
    { t: 'path', p: { d: 'M12 17.8v3.2' } },
  ],
  send: [
    { t: 'path', p: { d: 'M12 19.5v-15' } },
    { t: 'path', p: { d: 'm5.5 11 6.5-6.5 6.5 6.5' } },
  ],
  sparkle: [
    { t: 'path', p: { d: 'M12 3.5 13.9 9 19.4 11l-5.5 2-1.9 5.5-1.9-5.5L4.6 11l5.5-2L12 3.5Z' } },
  ],
  clock: [
    { t: 'circle', p: { cx: '12', cy: '12', r: '8.6' } },
    { t: 'path', p: { d: 'M12 6.9V12l3.4 2' } },
  ],
  doc: [
    {
      t: 'path',
      p: { d: 'M13.5 3.4H7a2 2 0 0 0-2 2v13.2a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8.9l-5.5-5.5Z' },
    },
    { t: 'path', p: { d: 'M13.4 3.6v5.2h5.3' } },
    { t: 'path', p: { d: 'M8.4 13.3h7M8.4 16.6h4.6' } },
  ],
  bank: [
    { t: 'path', p: { d: 'M3.6 9.6 12 4.4l8.4 5.2' } },
    { t: 'path', p: { d: 'M5.8 10.6v7.9M10 10.6v7.9M14 10.6v7.9M18.2 10.6v7.9' } },
    { t: 'path', p: { d: 'M3.4 20.3h17.2' } },
  ],
  edit: [{ t: 'path', p: { d: 'M16.2 4.4a2.1 2.1 0 0 1 3 3L9.5 17.1l-4 1 1-4 9.7-9.7Z' } }],
  target: [
    { t: 'circle', p: { cx: '12', cy: '12', r: '8.4' } },
    { t: 'circle', p: { cx: '12', cy: '12', r: '3.6' } },
    { t: 'path', p: { d: 'M12 1.8v2.6M12 19.6v2.6M22.2 12h-2.6M4.4 12H1.8' } },
  ],
  wallet: [
    { t: 'rect', p: { x: '3.4', y: '5.8', width: '17.2', height: '13', rx: '2.5' } },
    { t: 'path', p: { d: 'M3.4 10h17.2' } },
    { t: 'path', p: { d: 'M16.6 14.6h1.6' } },
  ],
  globe: [
    { t: 'circle', p: { cx: '12', cy: '12', r: '8.6' } },
    { t: 'path', p: { d: 'M3.6 12h16.8' } },
    {
      t: 'path',
      p: {
        d: 'M12 3.4c2.2 2.4 3.3 5.3 3.3 8.6S14.2 18.2 12 20.6c-2.2-2.4-3.3-5.3-3.3-8.6S9.8 5.8 12 3.4Z',
      },
    },
  ],
};

export type IconName = keyof typeof PATHS;

export type IconProps = {
  name: IconName;
  size?: number;
  color?: string;
  strokeWidth?: number;
};

export function Icon({ name, size = 24, color = colors.text, strokeWidth = 1.7 }: IconProps) {
  const els = PATHS[name] ?? [];
  return (
    <Svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke={color}
      strokeWidth={strokeWidth}
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      {els.map((el, i) => {
        const sw = el.p.strokeWidth ? Number(el.p.strokeWidth) : undefined;
        if (el.t === 'path') return <Path key={i} d={el.p.d} strokeWidth={sw} />;
        if (el.t === 'rect')
          return (
            <Rect
              key={i}
              x={el.p.x}
              y={el.p.y}
              width={el.p.width}
              height={el.p.height}
              rx={el.p.rx}
              strokeWidth={sw}
            />
          );
        return <Circle key={i} cx={el.p.cx} cy={el.p.cy} r={el.p.r} strokeWidth={sw} />;
      })}
    </Svg>
  );
}
