/**
 * Stands in while a route chunk arrives.
 *
 * The storefront shape is the header every page below the home page opens
 * with: the dark cropmarked band, the same wrapper padding, the meta rule, the
 * display heading, the lead, and the colour bar closing it. Each bar carries
 * the box its own line occupies, so the heading lands where the bar was rather
 * than near it, and the band is the height the real one resolves to. A change
 * to that header belongs here in the same edit.
 *
 * `panel` drops the band for the portal and admin shells, which open on a
 * panel rather than a header and would be wrong behind a dark hero.
 *
 * The bars are held at zero opacity for the first 300ms by animate-deferred-in,
 * so a chunk that lands from cache never flashes a placeholder. The band itself
 * paints immediately and holds the box throughout.
 */
export default function RouteFallback({ className = '', panel = false }) {
  if (panel) {
    return (
      <div className={`w-full ${className}`} aria-busy="true" data-placeholder="route">
        <div className="mx-auto min-h-[332px] max-w-[1400px] px-5 pt-16 sm:px-8">
          <div className="animate-deferred-in space-y-4" aria-hidden="true">
            <div className="h-3 w-32 bg-paper-100/8" />
            <div className="h-16 w-3/4 bg-paper-100/8 sm:h-20" />
            <div className="h-4 w-full max-w-xl bg-paper-100/8" />
            <div className="h-4 w-2/3 max-w-md bg-paper-100/8" />
          </div>
        </div>
        <span className="sr-only" role="status" aria-live="polite">
          Loading
        </span>
      </div>
    );
  }

  return (
    <div className={`w-full ${className}`} aria-busy="true" data-placeholder="route">
      <section
        data-skeleton="hero"
        className="cropmarks border-b border-paper-100/10 bg-ink-950 text-paper-100/40"
      >
        <div className="mx-auto max-w-[1400px] px-5 pb-12 pt-14 sm:px-8 sm:pt-20">
          <div className="animate-deferred-in" aria-hidden="true">
            {/* The meta rule carries its own bottom padding and border, so the
                box it holds is the kicker's line plus that padding rather than
                a height chosen to look close. */}
            <div className="border-b border-paper-100/12 pb-4">
              <div data-skeleton="meta" className="h-[11.2px] w-32 bg-paper-100/8" />
            </div>
            <div data-skeleton="headline" className="mt-8 h-24 w-full bg-paper-100/8" />
            <div data-skeleton="lead" className="mt-6 h-6 w-full max-w-xl bg-paper-100/8" />
          </div>
        </div>
        <div className="colorbar h-2" aria-hidden="true" />
      </section>
      <span className="sr-only" role="status" aria-live="polite">
        Loading
      </span>
    </div>
  );
}
