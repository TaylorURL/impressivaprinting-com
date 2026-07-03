// Print-shop visual language: CMYK ink bar + registration target.
// These are the studio's signature marks — used as structural accents, not decoration.

export function ColorBar({ className = '' }) {
  return (
    <div className={`colorbar ${className}`} aria-hidden>
      <span className="bg-proc-c" />
      <span className="bg-proc-m" />
      <span className="bg-proc-y" />
      <span className="bg-ink-950" />
      <span className="bg-paper-100" />
      <span className="bg-flare" />
    </div>
  );
}

export function Registration({ className = '' }) {
  return <span className={`registration inline-block ${className}`} aria-hidden />;
}

export function Crosshair({ className = '' }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" aria-hidden>
      <circle cx="12" cy="12" r="6.5" strokeWidth="1" />
      <path d="M12 0v7M12 17v7M0 12h7M17 12h7" strokeWidth="1" />
    </svg>
  );
}
