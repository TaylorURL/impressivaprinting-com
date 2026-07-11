/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        ink: {
          950: '#07080a',
          900: '#0c0e11',
          850: '#131619',
          800: '#1b1f24',
          700: '#272c33',
          600: '#3a424b',
        },
        // Cool concrete "paper" — industrial, not warm cream.
        paper: {
          100: '#d2d6db',
          200: '#c0c5cc',
          300: '#a6adb5',
          ink: '#0e1013',
        },
        flare: '#e5352b',
        'flare-deep': '#b81f16',
        volt: '#2f6bff',
        // Semantic status swatches (dashboard job states) — no CMYK rainbow.
        proc: {
          c: '#4b9fe0',
          m: '#6b7683',
          y: '#34c77b',
        },
      },
      fontFamily: {
        display: ['Anton', 'Impact', 'sans-serif'],
        head: ['Archivo', 'system-ui', 'sans-serif'],
        body: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['"Space Mono"', 'ui-monospace', 'monospace'],
      },
      letterSpacing: {
        tightest: '-0.045em',
        label: '0.28em',
      },
      keyframes: {
        shine: {
          '0%': { transform: 'translateX(-120%) skewX(-18deg)' },
          '60%, 100%': { transform: 'translateX(240%) skewX(-18deg)' },
        },
        'bar-pulse': {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.55' },
        },
      },
      animation: {
        shine: 'shine 5s ease-in-out infinite',
        'bar-pulse': 'bar-pulse 3s ease-in-out infinite',
      },
      transitionTimingFunction: {
        editorial: 'cubic-bezier(0.16, 1, 0.3, 1)',
      },
    },
  },
  plugins: [],
};
