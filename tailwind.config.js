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
        flare: '#ff5205',
        'flare-deep': '#d83d00',
        volt: '#2f6bff',
        // Industrial ink swatches (drove the old CMYK bar; no pink/yellow).
        proc: {
          c: '#2f6bff',
          m: '#6b7683',
          y: '#ff9e1b',
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
        'fade-rise': {
          '0%': { opacity: '0', transform: 'translateY(14px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        blink: {
          '0%, 49%': { opacity: '1' },
          '50%, 100%': { opacity: '0' },
        },
        scan: {
          '0%': { transform: 'translateY(-100%)' },
          '100%': { transform: 'translateY(100vh)' },
        },
        drift: {
          '0%': { backgroundPosition: '0 0' },
          '100%': { backgroundPosition: '40px 40px' },
        },
        shine: {
          '0%': { transform: 'translateX(-120%) skewX(-18deg)' },
          '60%, 100%': { transform: 'translateX(240%) skewX(-18deg)' },
        },
        'spin-slow': {
          '0%': { transform: 'rotate(0deg)' },
          '100%': { transform: 'rotate(360deg)' },
        },
        glitch: {
          '0%, 92%, 100%': { transform: 'translate(0)', filter: 'none' },
          '93%': { transform: 'translate(-2px, 1px)' },
          '95%': { transform: 'translate(2px, -1px)' },
          '97%': { transform: 'translate(-1px, -1px)' },
        },
        'bar-pulse': {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.55' },
        },
      },
      animation: {
        marquee: 'marquee 34s linear infinite',
        'marquee-rev': 'marquee-rev 40s linear infinite',
        'fade-rise': 'fade-rise 700ms cubic-bezier(0.16, 1, 0.3, 1) both',
        blink: 'blink 1.1s steps(1) infinite',
        scan: 'scan 7s linear infinite',
        drift: 'drift 6s linear infinite',
        shine: 'shine 5s ease-in-out infinite',
        'spin-slow': 'spin-slow 14s linear infinite',
        glitch: 'glitch 4s steps(1) infinite',
        'bar-pulse': 'bar-pulse 3s ease-in-out infinite',
      },
      transitionTimingFunction: {
        editorial: 'cubic-bezier(0.16, 1, 0.3, 1)',
      },
    },
  },
  plugins: [],
};
