// Print-shop visual language: ink registration bar + registration target.
// These are the studio's signature marks — used as structural accents, not decoration.
// Red-and-steel duotone, not a CMYK rainbow.

export function ColorBar({ className = '' }) {
  return (
    <div className={`colorbar ${className}`} aria-hidden>
      <span className="bg-flare" />
      <span className="bg-flare-deep" />
      <span className="bg-paper-300" />
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
