/** @type {import('tailwindcss').Config} */

// Colours resolve from the token block in src/index.css so a class works in
// all three themes. The channel form is what lets `bg-ink-950/70` still apply
// an alpha on top of a variable.
const channel = (name) => `rgb(var(${name}) / <alpha-value>)`;

export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  // index.html carries the fallback @font-face blocks, and the scanner
  // reads `font-display` there as a request for the Anton family utility.
  // Nothing sets that class, so what it emits is a rule on the sheet that
  // blocks the first paint and that no element can ever match.
  blocklist: ['font-display'],
  theme: {
    extend: {
      colors: {
        ink: {
          950: channel('--ink-950'),
          900: channel('--ink-900'),
          850: channel('--ink-850'),
          800: channel('--ink-800'),
          700: channel('--ink-700'),
          600: channel('--ink-600'),
        },
        // Cool concrete, not warm cream. `50` is the near-white sheet behind full
        // light sections; `100` is the softer tone for text on dark.
        paper: {
          50: channel('--paper-50'),
          100: channel('--paper-100'),
          200: channel('--paper-200'),
          300: channel('--paper-300'),
          ink: channel('--paper-ink'),
        },
        flare: channel('--flare'),
        'flare-deep': channel('--flare-deep'),
        volt: channel('--volt'),
        // Dashboard job states. Deliberately muted so they read as status, not brand.
        proc: {
          c: channel('--proc-c'),
          m: channel('--proc-m'),
          y: channel('--proc-y'),
        },
      },
      // One layer scale, mirroring --z-* in the token block. The nav sits above
      // every in-page sticky and a modal sits above the nav.
      zIndex: {
        base: 'var(--z-base)',
        raised: 'var(--z-raised)',
        scrim: 'var(--z-scrim)',
        media: 'var(--z-media)',
        caption: 'var(--z-caption)',
        dropdown: 'var(--z-dropdown)',
        sticky: 'var(--z-sticky)',
        nav: 'var(--z-nav)',
        overlay: 'var(--z-overlay)',
        modal: 'var(--z-modal)',
        toast: 'var(--z-toast)',
      },
      boxShadow: {
        card: 'var(--shadow-card)',
        'card-flare': 'var(--shadow-card-flare)',
        drawer: 'var(--shadow-drawer)',
        palette: 'var(--shadow-palette)',
        'nav-active': 'var(--shadow-nav-active)',
        'tab-active': 'var(--shadow-tab-active)',
        'field-focus': 'var(--shadow-field-focus)',
      },
      fontFamily: {
        display: ['Anton', 'Anton Fallback', 'Impact', 'sans-serif'],
        head: ['Archivo', 'Archivo Fallback', 'system-ui', 'sans-serif'],
        body: ['Inter', 'Inter Fallback', 'system-ui', 'sans-serif'],
        mono: ['"Space Mono"', '"Space Mono Fallback"', 'ui-monospace', 'monospace'],
      },
      // The codebase writes weights numerically (font-700) and leans on
      // off-scale alpha steps (/2, /8, /12); without these entries Tailwind
      // silently generates nothing for any of them.
      fontWeight: {
        400: '400',
        500: '500',
        600: '600',
        700: '700',
        800: '800',
      },
      opacity: {
        2: '0.02',
        8: '0.08',
        12: '0.12',
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
          '100%': { transform: 'translateY(100dvh)' },
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
        // Panel micro-motion: fast and subtle, tool speeds not marketing speeds.
        'panel-in': {
          '0%': { opacity: '0', transform: 'translateY(4px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        'pop-in': {
          '0%': { opacity: '0', transform: 'scale(0.98) translateY(-4px)' },
          '100%': { opacity: '1', transform: 'scale(1) translateY(0)' },
        },
        'overlay-in': {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        // Held at zero until the delay elapses, so a route that resolves
        // quickly never flashes a placeholder.
        'deferred-in': {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
      },
      animation: {
        marquee: 'marquee 34s linear infinite',
        'marquee-rev': 'marquee-rev 40s linear infinite',
        'fade-rise': 'fade-rise 300ms cubic-bezier(0.16, 1, 0.3, 1) both',
        blink: 'blink 1.1s steps(1) infinite',
        scan: 'scan 7s linear infinite',
        drift: 'drift 6s linear infinite',
        shine: 'shine 5s linear infinite',
        'spin-slow': 'spin-slow 14s linear infinite',
        glitch: 'glitch 4s steps(1) infinite',
        'bar-pulse': 'bar-pulse 3s ease-out infinite',
        'panel-in': 'panel-in 200ms cubic-bezier(0.16, 1, 0.3, 1) both',
        'pop-in': 'pop-in 150ms cubic-bezier(0.16, 1, 0.3, 1) both',
        'overlay-in': 'overlay-in 120ms ease-out both',
        'deferred-in': 'deferred-in 200ms ease-out 300ms both',
      },
      transitionTimingFunction: {
        editorial: 'cubic-bezier(0.16, 1, 0.3, 1)',
      },
    },
  },
  plugins: [],
};
