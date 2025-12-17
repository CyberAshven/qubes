/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Background Layers
        'bg-primary': '#0a0e17',
        'bg-secondary': '#111827',
        'bg-tertiary': '#1a1f2e',
        'bg-quaternary': '#242b3d',

        // Glass Effects
        'glass-bg': 'rgba(17, 24, 39, 0.6)',
        'glass-border': 'rgba(148, 163, 184, 0.1)',
        'glass-highlight': 'rgba(255, 255, 255, 0.05)',

        // Neon Accents
        'accent-primary': '#00BCD4',
        'accent-secondary': '#b47cff',
        'accent-success': '#00BCD4',
        'accent-warning': '#ffaa00',
        'accent-danger': '#ff3366',
        'accent-info': '#00d4ff',

        // Text
        'text-primary': '#f8fafc',
        'text-secondary': '#cbd5e1',
        'text-tertiary': '#64748b',
        'text-disabled': '#475569',
      },
      fontFamily: {
        primary: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Consolas', 'monospace'],
        display: ['Orbitron', 'sans-serif'],
        cyber: ['Rajdhani', 'sans-serif'],
      },
      boxShadow: {
        'glow-primary': '0 0 20px rgba(0, 188, 212, 0.4)',
        'glow-primary-strong': '0 0 30px rgba(0, 188, 212, 0.6)',
        'glow-secondary': '0 0 20px rgba(180, 124, 255, 0.4)',
        'glow-danger': '0 0 20px rgba(255, 51, 102, 0.4)',
        'glass': '0 8px 32px 0 rgba(0, 0, 0, 0.37), inset 0 1px 0 0 rgba(255, 255, 255, 0.05)',
        'glass-hover': '0 12px 48px 0 rgba(0, 0, 0, 0.5), inset 0 1px 0 0 rgba(255, 255, 255, 0.05)',
      },
      backdropBlur: {
        glass: '16px',
      },
      keyframes: {
        pulse: {
          '0%, 100%': { boxShadow: '0 0 30px rgba(0, 188, 212, 0.6)' },
          '50%': { boxShadow: '0 0 40px rgba(0, 188, 212, 0.8)' },
        },
        shimmer: {
          '0%': { backgroundPosition: '200% 0' },
          '100%': { backgroundPosition: '-200% 0' },
        },
      },
      animation: {
        pulse: 'pulse 2s ease-in-out infinite',
        shimmer: 'shimmer 2s linear infinite',
      },
    },
  },
  plugins: [],
}
