// Design tokens matching the #07090f dark theme used across all static HTML files

export const COLORS = {
  bg: '#07090f',
  cardBg: 'rgba(26,32,44,.95)',
  cardBorder: 'rgba(255,255,255,.1)',
  textPrimary: '#e2e8f0',
  textMuted: '#94a3b8',
  textDisabled: '#64748b',
  gold: '#f59e0b',
  blue: '#3b82f6',
  blueMuted: 'rgba(59,130,246,.18)',
  blueText: '#93c5fd',
  green: '#48bb78',
  red: '#ef4444',
  codeText: '#fcd34d',
} as const;

export const SPACING = {
  xs: '4px',
  sm: '8px',
  md: '16px',
  lg: '24px',
  xl: '32px',
  xxl: '48px',
} as const;

export const BORDER_RADIUS = {
  sm: '6px',
  md: '10px',
  lg: '16px',
  xl: '20px',
  full: '9999px',
} as const;

export const FONT_SIZE = {
  xs: '0.75rem',
  sm: '0.875rem',
  base: '1rem',
  lg: '1.125rem',
  xl: '1.25rem',
  '2xl': '1.5rem',
  '3xl': '1.875rem',
} as const;

/** CSS string injected into document.head to set body background and font */
export const globalStyles = `
  *, *::before, *::after { box-sizing: border-box; }
  body {
    margin: 0;
    padding: 0;
    background: ${COLORS.bg};
    color: ${COLORS.textPrimary};
    font-family: 'Segoe UI', Arial, sans-serif;
    min-height: 100vh;
  }
  #root { min-height: 100vh; }
`.trim();
