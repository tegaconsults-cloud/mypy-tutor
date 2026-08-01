/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      fontFamily: {
        sora:    ['Sora', 'sans-serif'],
        inter:   ['Inter', 'sans-serif'],
        mono:    ['JetBrains Mono', 'Consolas', 'monospace'],
        league:  ['"League Spartan"', 'sans-serif'],
      },
      colors: {
        // Official MyPyTutor Brand
        brand: {
          blue:       '#0D47A1',   // Primary Blue
          'blue-2':   '#1565E8',   // Secondary Blue
          gold:       '#E0A300',   // Primary Gold
          'gold-2':   '#C98B00',   // Secondary Gold
          navy:       '#082B6B',   // Dark Navy
          white:      '#FFFFFF',
        },
        // UI semantic tokens
        primary: {
          50:  '#e8f0fe',
          100: '#c5d8fc',
          400: '#4d8af8',
          500: '#1565E8',
          600: '#0D47A1',
          700: '#082B6B',
          900: '#041540',
        },
        gold: {
          300: '#fcd34d',
          400: '#E0A300',
          500: '#C98B00',
          600: '#a06e00',
        },
        surface: {
          50:  '#f8faff',
          100: '#f0f4ff',
          800: '#0f1a2e',
          850: '#091427',
          900: '#060d1c',
          950: '#030810',
        },
      },
      backgroundImage: {
        'brand-gradient':   'linear-gradient(135deg, #0D47A1 0%, #1565E8 50%, #082B6B 100%)',
        'gold-gradient':    'linear-gradient(135deg, #E0A300 0%, #C98B00 100%)',
        'hero-gradient':    'linear-gradient(135deg, #030810 0%, #060d1c 40%, #0D47A1 100%)',
        'card-gradient':    'linear-gradient(135deg, rgba(13,71,161,0.15) 0%, rgba(6,13,28,0.9) 100%)',
        'glass':            'linear-gradient(135deg, rgba(255,255,255,0.06) 0%, rgba(255,255,255,0.02) 100%)',
        'gold-shimmer':     'linear-gradient(90deg, transparent, rgba(224,163,0,0.3), transparent)',
      },
      boxShadow: {
        'brand':        '0 4px 24px rgba(13,71,161,0.4)',
        'brand-lg':     '0 8px 48px rgba(13,71,161,0.5)',
        'gold':         '0 4px 20px rgba(224,163,0,0.35)',
        'glass':        '0 8px 32px rgba(0,0,0,0.5), inset 0 1px 0 rgba(255,255,255,0.08)',
        'card':         '0 4px 24px rgba(0,0,0,0.4)',
        'card-hover':   '0 12px 48px rgba(0,0,0,0.6), 0 0 0 1px rgba(13,71,161,0.3)',
        'glow-blue':    '0 0 32px rgba(21,101,232,0.5)',
        'glow-gold':    '0 0 24px rgba(224,163,0,0.4)',
      },
      borderRadius: {
        '2xl': '16px',
        '3xl': '20px',
        '4xl': '24px',
      },
      animation: {
        'fade-in':       'fadeIn 0.4s ease forwards',
        'slide-up':      'slideUp 0.35s ease forwards',
        'slide-down':    'slideDown 0.25s ease forwards',
        'scale-in':      'scaleIn 0.2s ease forwards',
        'float':         'float 6s ease-in-out infinite',
        'shimmer':       'shimmer 2s ease-in-out infinite',
        'pulse-gold':    'pulseGold 2s ease-in-out infinite',
        'bounce-subtle': 'bounceSubtle 1.4s ease-in-out infinite',
        'typing':        'typing 1.2s steps(3) infinite',
        'spin-slow':     'spin 8s linear infinite',
      },
      keyframes: {
        fadeIn:      { '0%': { opacity: '0' }, '100%': { opacity: '1' } },
        slideUp:     { '0%': { opacity: '0', transform: 'translateY(20px)' }, '100%': { opacity: '1', transform: 'translateY(0)' } },
        slideDown:   { '0%': { opacity: '0', transform: 'translateY(-10px)' }, '100%': { opacity: '1', transform: 'translateY(0)' } },
        scaleIn:     { '0%': { opacity: '0', transform: 'scale(0.95)' }, '100%': { opacity: '1', transform: 'scale(1)' } },
        float:       { '0%,100%': { transform: 'translateY(0)' }, '50%': { transform: 'translateY(-12px)' } },
        shimmer:     { '0%': { backgroundPosition: '-200% 0' }, '100%': { backgroundPosition: '200% 0' } },
        pulseGold:   { '0%,100%': { boxShadow: '0 0 16px rgba(224,163,0,0.2)' }, '50%': { boxShadow: '0 0 32px rgba(224,163,0,0.5)' } },
        bounceSubtle:{ '0%,100%': { transform: 'translateY(0)' }, '50%': { transform: 'translateY(-4px)' } },
        typing:      { '0%,100%': { opacity: '1' }, '50%': { opacity: '0' } },
      },
    },
  },
  plugins: [],
}
