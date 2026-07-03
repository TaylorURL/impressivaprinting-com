/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        ink: {
          950: '#08080a',
          900: '#0d0d10',
          850: '#141418',
          800: '#1b1b20',
          700: '#26262d',
          600: '#3a3a43',
        },
        paper: {
          100: '#f4efe3',
          200: '#ebe4d3',
          300: '#ddd3bd',
          ink: '#181510',
        },
        flare: '#ff3d1f',
        'flare-deep': '#e02c10',
        proc: {
          c: '#12b7d6',
          m: '#ff2e93',
          y: '#ffcf1a',
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
        marquee: {
          '0%': { transform: 'translateX(0)' },
          '100%': { transform: 'translateX(-50%)' },
        },
        'marquee-rev': {
          '0%': { transform: 'translateX(-50%)' },
          '100%': { transform: 'translateX(0)' },
        },
        reveal: {
          '0%': { transform: 'translateY(110%)' },
          '100%': { transform: 'translateY(0)' },
        },
        'fade-rise': {
          '0%': { opacity: '0', transform: 'translateY(14px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        blink: {
          '0%, 49%': { opacity: '1' },
          '50%, 100%': { opacity: '0' },
        },
      },
      animation: {
        marquee: 'marquee 38s linear infinite',
        'marquee-rev': 'marquee-rev 42s linear infinite',
        'fade-rise': 'fade-rise 700ms cubic-bezier(0.16, 1, 0.3, 1) both',
        blink: 'blink 1.1s steps(1) infinite',
      },
      transitionTimingFunction: {
        editorial: 'cubic-bezier(0.16, 1, 0.3, 1)',
      },
    },
  },
  plugins: [],
};
