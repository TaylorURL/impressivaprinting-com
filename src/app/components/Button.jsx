import { Link } from 'react-router-dom';

// Sharp editorial buttons — square corners, mono label, no gradients.
const VARIANTS = {
  flare: 'bg-flare text-white hover:bg-flare-deep',
  ink: 'bg-ink-950 text-paper-100 hover:bg-ink-850 border border-paper-100/15',
  paper: 'bg-paper-100 text-ink-950 hover:bg-paper-200',
  outline: 'border border-current text-paper-100 hover:bg-paper-100 hover:text-ink-950',
  'outline-ink': 'border border-ink-950/30 text-ink-950 hover:bg-ink-950 hover:text-paper-100',
};

const SIZES = {
  sm: 'px-4 py-2.5 text-[11px]',
  md: 'px-6 py-3.5 text-xs',
  lg: 'px-8 py-4 text-xs',
};

function classes({ variant, size, full }) {
  return [
    'pressable group inline-flex items-center justify-center gap-2.5 font-mono font-700 uppercase tracking-[0.18em]',
    'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-flare focus-visible:ring-offset-2 focus-visible:ring-offset-ink-950',
    VARIANTS[variant] || VARIANTS.flare,
    SIZES[size] || SIZES.md,
    full ? 'w-full' : '',
  ].join(' ');
}

export default function Button({
  as = 'button',
  to,
  href,
  variant = 'flare',
  size = 'md',
  full = false,
  className = '',
  children,
  ...rest
}) {
  const cls = `${classes({ variant, size, full })} ${className}`;
  if (to) {
    return (
      <Link to={to} className={cls} {...rest}>
        {children}
      </Link>
    );
  }
  if (href) {
    return (
      <a href={href} className={cls} {...rest}>
        {children}
      </a>
    );
  }
  const Tag = as;
  return (
    <Tag className={cls} {...rest}>
      {children}
    </Tag>
  );
}
