/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        ink: {
          950: 'var(--ink-950)',
          900: 'var(--ink-900)',
          800: 'var(--ink-800)',
          700: 'var(--ink-700)',
        },
        magenta: 'var(--neon-magenta)',
        cyan: 'var(--neon-cyan)',
        acid: 'var(--neon-acid)',
        sunset: 'var(--neon-sunset)',
        gold: 'var(--neon-gold)',
      },
      fontFamily: {
        display: ['Anton', 'Impact', 'sans-serif'],
        graff: ['"Permanent Marker"', 'cursive'],
        head: ['"Space Grotesk"', 'system-ui', 'sans-serif'],
        body: ['Inter', 'system-ui', 'sans-serif'],
      },
      boxShadow: {
        glass: '0 8px 32px 0 rgba(0, 0, 0, 0.55), inset 0 1px 0 0 rgba(255, 255, 255, 0.08)',
        'neon-magenta': '0 0 24px -2px rgba(255, 45, 149, 0.65)',
        'neon-cyan': '0 0 24px -2px rgba(32, 227, 255, 0.6)',
        'neon-acid': '0 0 24px -2px rgba(166, 255, 0, 0.55)',
      },
      backgroundImage: {
        'grid-street':
          'linear-gradient(rgba(255,255,255,0.035) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.035) 1px, transparent 1px)',
      },
      backgroundSize: {
        grid: '44px 44px',
      },
      keyframes: {
        'float-slow': {
          '0%, 100%': { transform: 'translateY(0) rotate(0deg)' },
          '50%': { transform: 'translateY(-18px) rotate(1.5deg)' },
        },
        'marquee': {
          '0%': { transform: 'translateX(0)' },
          '100%': { transform: 'translateX(-50%)' },
        },
        'flicker': {
          '0%, 18%, 22%, 25%, 53%, 57%, 100%': { opacity: '1' },
          '20%, 24%, 55%': { opacity: '0.55' },
        },
        'rise': {
          '0%': { opacity: '0', transform: 'translateY(16px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        'shine': {
          '0%': { transform: 'translateX(-120%) skewX(-20deg)' },
          '100%': { transform: 'translateX(220%) skewX(-20deg)' },
        },
      },
      animation: {
        'float-slow': 'float-slow 9s ease-in-out infinite',
        marquee: 'marquee 32s linear infinite',
        flicker: 'flicker 4s linear infinite',
        rise: 'rise 600ms cubic-bezier(0.23, 1, 0.32, 1) both',
        shine: 'shine 1.1s cubic-bezier(0.23, 1, 0.32, 1)',
      },
      transitionTimingFunction: {
        street: 'cubic-bezier(0.23, 1, 0.32, 1)',
      },
    },
  },
  plugins: [],
};
