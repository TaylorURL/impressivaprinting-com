import { Link } from 'react-router-dom';

const VARIANTS = {
  primary:
    'street-gradient text-ink-950 shadow-neon-magenta hover:shadow-[0_0_36px_-2px_rgba(255,45,149,0.8)]',
  cyan: 'cyan-gradient text-ink-950 shadow-neon-cyan',
  glass: 'glass glass-sheen text-white hover:border-white/25',
  outline: 'border border-white/20 text-white hover:border-magenta/70 hover:text-white',
  ghost: 'text-white/70 hover:text-white',
};

const SIZES = {
  sm: 'px-4 py-2 text-sm',
  md: 'px-6 py-3 text-sm',
  lg: 'px-8 py-4 text-base',
};

function classes({ variant, size, full }) {
  return [
    'pressable inline-flex items-center justify-center gap-2 rounded-full font-head font-700 uppercase tracking-wide',
    'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan/70 focus-visible:ring-offset-2 focus-visible:ring-offset-ink-950',
    VARIANTS[variant] || VARIANTS.primary,
    SIZES[size] || SIZES.md,
    full ? 'w-full' : '',
  ].join(' ');
}

export default function Button({
  as = 'button',
  to,
  href,
  variant = 'primary',
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
