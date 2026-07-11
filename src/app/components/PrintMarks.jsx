// Print-shop ink registration bar — the studio's signature mark, used as a
// structural accent rather than decoration. Red-and-steel duotone, not a CMYK rainbow.
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
