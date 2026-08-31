import { Link } from 'react-router-dom';
import { ORDER_STATUSES } from '@constants/orders.js';

// Panel design tokens. The marketing site is deliberately hard-edged; the
// panels are software, so surfaces here get radii, elevation, and quieter
// labels. Mono type is reserved for technical values: order numbers,
// timestamps, column headers.

export const LABEL = 'mb-2 block text-xs font-500 text-paper-100/55';
export const FIELD =
  'control-sm w-full rounded-md border border-paper-100/15 bg-ink-950 px-3 py-2 text-[13px] text-paper-100 placeholder:text-paper-100/30 outline-none transition-[border-color,box-shadow] focus:border-flare/70 focus:shadow-field-focus';
export const AREA = FIELD;

const CARD = 'rounded-lg border border-paper-100/10 bg-ink-900 shadow-card';
export const CARD_CLASS = CARD;

const BTN_VARIANTS = {
  primary: 'bg-flare text-white hover:bg-flare-deep',
  flare: 'bg-flare text-white hover:bg-flare-deep',
  secondary:
    'border border-paper-100/15 bg-ink-850 text-paper-100/80 hover:border-paper-100/30 hover:text-paper-100',
  outline:
    'border border-paper-100/15 bg-ink-850 text-paper-100/80 hover:border-paper-100/30 hover:text-paper-100',
};
// Heights come from the shared control token rather than from padding, so a
// button lands on the same baseline as the input beside it.
const BTN_SIZES = {
  sm: 'control-sm px-3 py-1',
  md: 'control-sm px-4 py-2',
  lg: 'control px-5 py-3',
};

export function PanelButton({
  as = 'button',
  to,
  variant = 'primary',
  size = 'md',
  full = false,
  className = '',
  children,
  ...rest
}) {
  const cls = [
    'pressable inline-flex items-center justify-center gap-2 rounded-md text-[13px] font-600 transition-colors',
    'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-flare/60 focus-visible:ring-offset-2 focus-visible:ring-offset-ink-950',
    'disabled:pointer-events-none disabled:opacity-40',
    BTN_VARIANTS[variant] || BTN_VARIANTS.primary,
    BTN_SIZES[size] || BTN_SIZES.md,
    full ? 'w-full' : '',
    className,
  ].join(' ');
  if (to) {
    return (
      <Link to={to} className={cls} {...rest}>
        {children}
      </Link>
    );
  }
  const Tag = as;
  return (
    <Tag className={cls} {...rest}>
      {children}
    </Tag>
  );
}

export function StatusChip({ status, pulse = false, className = '' }) {
  const meta = ORDER_STATUSES[status] || {
    label: status,
    badge: 'bg-paper-100/5 text-paper-100/50 border-paper-100/15',
  };
  return (
    <span
      className={`spec inline-flex items-center whitespace-nowrap rounded-full border px-2 py-1 text-[10px] uppercase tracking-[0.1em] ${meta.badge} ${className}`}
    >
      <span
        className={`mr-2 inline-block h-1.5 w-1.5 rounded-full bg-current ${pulse ? 'animate-bar-pulse' : ''}`}
      />
      {meta.label}
    </span>
  );
}

export function SectionTitle({ children, aside, className = '' }) {
  return (
    <div className={`mb-3 flex items-baseline justify-between ${className}`}>
      <span className="text-[13px] font-600 text-paper-100/80">{children}</span>
      {aside ? <span className="text-xs text-paper-100/40">{aside}</span> : null}
    </div>
  );
}

const STAT_COLS = {
  2: 'sm:grid-cols-2',
  3: 'sm:grid-cols-3',
  4: 'sm:grid-cols-4',
};

// Static numbers. A dashboard reports; it doesn't animate.
export function StatGrid({ stats }) {
  return (
    <div
      className={`grid grid-cols-2 overflow-hidden ${CARD} ${STAT_COLS[stats.length] || 'sm:grid-cols-4'}`}
    >
      {stats.map((s, i) => (
        <div key={s.label} className={`px-4 py-3 ${i !== 0 ? 'border-l border-paper-100/8' : ''}`}>
          <p className="font-head text-2xl font-700 tabular-nums text-paper-100">{s.value}</p>
          <p className="mt-1 text-xs text-paper-100/50">{s.label}</p>
        </div>
      ))}
    </div>
  );
}

// Shown while a view waits on the database; sized like the list it becomes
// so the layout doesn't jump when data lands.
export function PanelLoading({ label = 'Loading…' }) {
  return (
    <div
      className="rounded-lg border border-dashed border-paper-100/15 px-5 py-9 text-center"
      role="status"
      aria-live="polite"
    >
      <span className="spec text-[10px] uppercase tracking-[0.2em] text-paper-100/40">
        <span className="mr-2 inline-block h-1.5 w-1.5 animate-bar-pulse rounded-full bg-flare align-middle" />
        {label}
      </span>
    </div>
  );
}

// Shown when a read against the database fails outright.
export function PanelError({ message, onRetry }) {
  return (
    <div className="rounded-lg border border-flare/30 bg-flare/5 px-5 py-9 text-center">
      <p className="text-[13px] text-paper-100/75">{message || 'Could not load this view.'}</p>
      {onRetry ? (
        <button
          onClick={onRetry}
          className="pressable mt-3 rounded-md border border-paper-100/15 bg-ink-850 px-3 py-2 text-xs font-600 text-paper-100/80 transition-colors hover:border-paper-100/30 hover:text-paper-100"
        >
          Try Again
        </button>
      ) : null}
    </div>
  );
}

export function EmptyState({ title, body, children }) {
  return (
    <div className="rounded-lg border border-dashed border-paper-100/15 px-5 py-9 text-center">
      <p className="text-[13px] text-paper-100/60">{title}</p>
      {body ? <p className="mx-auto mt-1 max-w-sm text-xs text-paper-100/40">{body}</p> : null}
      {children ? <div className="mt-4">{children}</div> : null}
    </div>
  );
}

export function FilterTabs({ options, value, onChange }) {
  return (
    <div className="flex flex-wrap gap-2">
      {options.map((opt) => (
        <button
          key={opt.value}
          onClick={() => onChange(opt.value)}
          className={`pressable rounded-md px-3 py-1 text-xs font-500 transition-colors ${
            value === opt.value
              ? 'bg-flare/10 text-flare shadow-tab-active'
              : 'text-paper-100/50 hover:bg-paper-100/5 hover:text-paper-100'
          }`}
        >
          {opt.label}
          {typeof opt.count === 'number' ? (
            <span className={`ml-1 ${value === opt.value ? 'text-flare/60' : 'text-paper-100/30'}`}>
              {opt.count}
            </span>
          ) : null}
        </button>
      ))}
    </div>
  );
}

// Key/value rows. Each item is `{ k, value }`; a null or undefined value drops
// its row and an empty string renders as a dash.
export function SpecList({ items }) {
  const rows = items.filter((item) => item.value !== undefined && item.value !== null);
  return (
    <dl>
      {rows.map((item) => (
        <div
          key={item.k}
          className="flex items-baseline justify-between gap-4 border-b border-paper-100/8 py-2 last:border-b-0"
        >
          <dt className="shrink-0 text-xs text-paper-100/45">{item.k}</dt>
          <dd className="min-w-0 text-right text-[13px] text-paper-100/85">
            {item.value === '' ? '-' : item.value}
          </dd>
        </div>
      ))}
    </dl>
  );
}

export function PanelCard({ title, aside, className = '', children }) {
  return (
    <section className={`${CARD} p-4 ${className}`}>
      {title ? <SectionTitle aside={aside}>{title}</SectionTitle> : null}
      {children}
    </section>
  );
}
