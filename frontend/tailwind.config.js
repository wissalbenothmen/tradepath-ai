/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // Brand — financial/authority navy → electric blue → cyan
        brand: {
          50: '#eef4ff',
          100: '#dbe6ff',
          200: '#b8cdff',
          300: '#88aaff',
          400: '#5b85ff',
          500: '#3460ff',
          600: '#1d44e8',
          700: '#1734bd',
          800: '#172d96',
          900: '#0b1f4d',
          950: '#080f2b',
        },
        // AI accent — purple → cyan (used for AI surfaces only)
        ai: {
          50: '#f5f3ff',
          100: '#ede9fe',
          400: '#a78bfa',
          500: '#8b5cf6',
          600: '#7c3aed',
          700: '#6d28d9',
          cyan: '#06b6d4',
          glow: '#a855f7',
        },
        // Surfaces — semantic backgrounds
        surface: {
          DEFAULT: '#ffffff',
          subtle: '#f8fafc',
          muted: '#f1f5f9',
          inverted: '#0b1220',
        },
      },
      fontFamily: {
        sans: [
          'Inter',
          'ui-sans-serif',
          'system-ui',
          '-apple-system',
          'Segoe UI',
          'Roboto',
          'sans-serif',
        ],
        mono: [
          'JetBrains Mono',
          'ui-monospace',
          'SFMono-Regular',
          'Menlo',
          'Consolas',
          'monospace',
        ],
      },
      fontSize: {
        // Tabular-numerals helper for KPIs is applied via .tabular utility.
        '2xs': ['0.6875rem', { lineHeight: '1rem' }],
      },
      boxShadow: {
        'soft-1': '0 1px 2px rgb(15 23 42 / 0.04), 0 1px 3px rgb(15 23 42 / 0.06)',
        'soft-2': '0 4px 16px -2px rgb(15 23 42 / 0.06), 0 2px 4px rgb(15 23 42 / 0.04)',
        'soft-3': '0 10px 28px -6px rgb(15 23 42 / 0.10), 0 4px 8px rgb(15 23 42 / 0.04)',
        'ai-glow': '0 0 0 1px rgb(124 58 237 / 0.25), 0 8px 24px -8px rgb(124 58 237 / 0.45)',
        'ai-glow-soft': '0 0 0 1px rgb(124 58 237 / 0.18), 0 4px 16px -6px rgb(124 58 237 / 0.30)',
      },
      backgroundImage: {
        'brand-gradient':
          'linear-gradient(135deg, #0b1f4d 0%, #1d44e8 50%, #06b6d4 100%)',
        'ai-gradient':
          'linear-gradient(135deg, #6d28d9 0%, #8b5cf6 45%, #06b6d4 100%)',
        'ai-subtle':
          'linear-gradient(135deg, rgb(124 58 237 / 0.08) 0%, rgb(6 182 212 / 0.08) 100%)',
        'grid-fade':
          'radial-gradient(circle at 50% 0%, rgb(124 58 237 / 0.10), transparent 60%)',
      },
      keyframes: {
        'slide-in': {
          '0%': { opacity: '0', transform: 'translateY(8px) scale(0.97)' },
          '100%': { opacity: '1', transform: 'translateY(0) scale(1)' },
        },
        'fade-in': {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        'thinking': {
          '0%, 80%, 100%': { opacity: '0.2', transform: 'scale(0.8)' },
          '40%': { opacity: '1', transform: 'scale(1)' },
        },
        'shimmer': {
          '0%': { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200% 0' },
        },
        'pulse-glow': {
          '0%, 100%': { boxShadow: '0 0 0 0 rgb(124 58 237 / 0.40)' },
          '50%': { boxShadow: '0 0 0 6px rgb(124 58 237 / 0)' },
        },
        'spin-slow': {
          '0%': { transform: 'rotate(0deg)' },
          '100%': { transform: 'rotate(360deg)' },
        },
        'gradient-shift': {
          '0%, 100%': { backgroundPosition: '0% 50%' },
          '50%': { backgroundPosition: '100% 50%' },
        },
        'cursor-blink': {
          '0%, 49%': { opacity: '1' },
          '50%, 100%': { opacity: '0' },
        },
      },
      animation: {
        'slide-in': 'slide-in 0.2s ease-out',
        'fade-in': 'fade-in 0.18s ease-out',
        'thinking': 'thinking 1.4s ease-in-out infinite',
        'shimmer': 'shimmer 2.4s linear infinite',
        'pulse-glow': 'pulse-glow 1.8s ease-in-out infinite',
        'spin-slow': 'spin-slow 12s linear infinite',
        'gradient-shift': 'gradient-shift 8s ease-in-out infinite',
        'cursor-blink': 'cursor-blink 1s steps(2) infinite',
      },
    },
  },
  plugins: [],
}
