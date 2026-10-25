// iBackHome design tokens as a Tailwind theme extension (React + TypeScript web app).
// Generated from 01-design-system/tokens.json. Merge into tailwind.config.ts:
//   import { ibhTheme } from './tailwind.tokens';
//   export default { theme: { extend: ibhTheme } } satisfies Config;
// If the existing repo does not use Tailwind, read tokens.css instead (CSS variables).
// Rule: status colours (ibh.status.*) only inside chips and alerts.

export const ibhTheme = {
  colors: {
    ibh: {
        'navy-900': '#00022E',
        'navy-800': '#10144A',
        'navy-700': '#1E2260',
        'navy-200': '#C9D3E3',
        'ink': '#0B1324',
        'slate': '#3A4354',
        'muted': '#5F6878',
        'white': '#FFFFFF',
        'mist': '#F4F8FB',
        'canvas': '#F1F3F5',
        'line': '#E4E8EE',
        'line-strong': '#7E889A',
        'frame': '#D5DBE3',
        'accent': '#2F5FC4',
        'accent-hover': '#1F4699',
        'accent-tint': '#E8EFFC',
        'row-highlight': '#F7FAFF',
        'focus-on-dark': '#7FA2E8',
        'escrow-bar': '#8C97AD',
        'placeholder': '#E6ECF3',
        'camera': '#1B2436',
      status: {
        ok: { bg: '#E7F4EC', fg: '#1E6B45' },
        warn: { bg: '#FDF1D8', fg: '#8A5300' },
        bad: { bg: '#FDECEA', fg: '#B42318' },
        neutral: { bg: '#EEF1F5', fg: '#4A5363' },
        info: { bg: '#E8EFFC', fg: '#2552B0' },
      },
      // Supplementary values found on approved boards (confirm or replace; see PACKAGE-REPORT.md)
      x: {
        'placeholder-border': '#C2CAD5',
        'map-land': '#E6E9ED',
        'map-block': '#E2E6EB',
        'whatsapp-wallpaper': '#ECE7DF',
        'whatsapp-bubble-out': '#DCE8FB',
        'chat-bg': '#ECE9E4',
        'on-navy-muted': '#9AA6BB',
        'ok-on-dark': '#8FD3AE',
        'bad-on-dark': '#F1C4BF',
        'bad-icon-on-dark': '#F4A79F',
        'destructive-hover': '#912018',
      },
    },
  },
  fontFamily: {
    sans: ['Inter', 'Segoe UI', 'Roboto', 'Arial', 'sans-serif'],
    mono: ['JetBrains Mono', 'ui-monospace', 'Menlo', 'Consolas', 'monospace'],
  },
  fontSize: {
        'display': ['56px', { lineHeight: '62px', fontWeight: '700', letterSpacing: '-0.02em' }],
        'h1': ['36px', { lineHeight: '44px', fontWeight: '700', letterSpacing: '-0.02em' }],
        'h2': ['28px', { lineHeight: '36px', fontWeight: '700', letterSpacing: '-0.02em' }],
        'h3': ['20px', { lineHeight: '28px', fontWeight: '600', letterSpacing: '-0.01em' }],
        'body-lg': ['16px', { lineHeight: '24px', fontWeight: '400', letterSpacing: '0' }],
        'body': ['15px', { lineHeight: '24px', fontWeight: '400', letterSpacing: '0' }],
        'small': ['14px', { lineHeight: '20px', fontWeight: '400', letterSpacing: '0' }],
        'caption': ['12px', { lineHeight: '16px', fontWeight: '600', letterSpacing: '0.06em' }],
        'android-body': ['15px', { lineHeight: '22px', fontWeight: '400', letterSpacing: '0' }],
        'ops-body': ['13px', { lineHeight: '19px', fontWeight: '400', letterSpacing: '0' }],
        'mono': ['13px', { lineHeight: '20px', fontWeight: '500', letterSpacing: '0' }],
  },
  spacing: { '4': '4px', '8': '8px', '12': '12px', '16': '16px', '20': '20px', '24': '24px', '32': '32px', '40': '40px', '48': '48px', '64': '64px' },
  borderRadius: { tag: '6px', control: '8px', card: '12px', dialog: '16px', sheet: '20px', device: '24px', pill: '999px' },
  boxShadow: { card: '0 1px 2px rgba(19,31,57,0.06)', raised: '0 4px 12px rgba(19,31,57,0.08)', dialog: '0 24px 48px rgba(11,19,36,0.24)' },
  minHeight: { target: '44px' },
  minWidth: { target: '44px' },
} as const;

export type IbhStatus = keyof typeof ibhTheme.colors.ibh.status;
