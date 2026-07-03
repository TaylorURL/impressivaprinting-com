// CSS "poster" placeholder for portfolio work — no photography needed.
// Builds a distinct printed-piece look per item from its accent + kind.
export default function WorkTile({ item, className = '' }) {
  return (
    <article
      className={`group relative flex flex-col overflow-hidden border border-paper-100/12 bg-ink-900 ${className}`}
    >
      {/* Poster face */}
      <div className="relative aspect-[4/5] w-full overflow-hidden">
        <div className="halftone pointer-events-none absolute inset-0 z-10 opacity-[0.06]" />
        <div
          className="absolute inset-0 transition-transform duration-700 ease-editorial group-hover:scale-105"
          style={{ backgroundColor: item.accent }}
        >
          <div
            className="absolute inset-0 opacity-90"
            style={{
              backgroundImage: `repeating-linear-gradient(-45deg, rgba(7,8,10,0) 0, rgba(7,8,10,0) 22px, rgba(7,8,10,0.14) 22px, rgba(7,8,10,0.14) 24px)`,
            }}
          />
          <div className="absolute inset-0 flex flex-col justify-between p-5">
            <div className="flex items-center justify-between">
              <span className="spec text-[10px] font-700 uppercase tracking-[0.2em] text-ink-950/70">
                {item.category}
              </span>
              <span className="spec text-[10px] text-ink-950/60">{item.year}</span>
            </div>
            <div className="display text-[2.6rem] leading-[0.82] text-ink-950 mix-blend-overlay">
              {item.title}
            </div>
          </div>
        </div>
      </div>

      {/* Caption */}
      <div className="flex items-center justify-between border-t border-paper-100/12 p-4">
        <div>
          <p className="font-head text-sm font-700 text-paper-100">{item.title}</p>
          <p className="spec mt-0.5 text-[11px] text-paper-100/45">{item.client}</p>
        </div>
        <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: item.accent }} />
      </div>
    </article>
  );
}
