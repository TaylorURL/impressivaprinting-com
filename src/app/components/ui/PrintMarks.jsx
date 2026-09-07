// Print marks read as structure, not ornament — keep them to the
// red-and-steel duotone rather than letting them drift into a CMYK rainbow.

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
