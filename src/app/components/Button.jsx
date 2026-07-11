import { Link } from 'react-router-dom';
import { Magnet } from '@reactbits';

// Sharp editorial buttons — square corners, mono label, no gradients.
const VARIANTS = {
  flare: 'shine bg-flare text-white hover:bg-flare-deep hover:-translate-y-0.5',
  volt: 'shine bg-volt text-white hover:brightness-110 hover:-translate-y-0.5',
  ink: 'bg-ink-950 text-paper-100 hover:bg-ink-850 border border-paper-100/15 hover:-translate-y-0.5',
  paper: 'bg-paper-100 text-ink-950 hover:bg-paper-200 hover:-translate-y-0.5',
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
  magnetic = false,
  className = '',
  children,
  ...rest
}) {
  const cls = `${classes({ variant, size, full })} ${className}`;

  let el;
  if (to) {
    el = (
      <Link to={to} className={cls} {...rest}>
        {children}
      </Link>
    );
  } else if (href) {
    el = (
      <a href={href} className={cls} {...rest}>
        {children}
      </a>
    );
  } else {
    const Tag = as;
    el = (
      <Tag className={cls} {...rest}>
        {children}
      </Tag>
    );
  }

  if (!magnetic) return el;
  return (
    <Magnet padding={70} magnetStrength={5} wrapperClassName={full ? 'block w-full' : 'inline-block'}>
      {el}
    </Magnet>
  );
}
