import Picture from '@components/Picture.jsx';

// `tone` only flips the frame and caption bar; the photo face is identical
// either way.
export default function WorkTile({ item, tone = 'ink', className = '' }) {
  const paper = tone === 'paper';
  const frame = paper ? 'border-ink-950/12 bg-white' : 'border-paper-100/12 bg-ink-900';
  const captionRule = paper ? 'border-ink-950/10' : 'border-paper-100/12';
  const titleText = paper ? 'text-ink-950' : 'text-paper-100';
  const subText = paper ? 'text-ink-950/45' : 'text-paper-100/45';

  return (
    <article
      className={`group relative flex flex-col overflow-hidden border ${frame} ${className}`}
    >
      <div className="relative aspect-[4/5] w-full overflow-hidden bg-ink-950">
        <div className="halftone pointer-events-none absolute inset-0 z-media opacity-[0.06]" />
        <Picture
          src={item.image}
          alt={`${item.title}, printed for ${item.client}`}
          width="800"
          height="1000"
          sizes="(min-width: 1024px) 30vw, (min-width: 640px) 42vw, 78vw"
          className="absolute inset-0 h-full w-full object-cover transition-transform duration-700 ease-editorial group-hover:scale-[1.04]"
        />
        {/* The scrim keeps the corner chips legible over any artwork. */}
        <div className="pointer-events-none absolute inset-x-0 top-0 z-scrim h-24 bg-gradient-to-b from-ink-950/75 to-transparent" />
        <div className="absolute inset-x-0 top-0 z-caption flex items-center justify-between p-5">
          <span className="spec text-[10px] font-700 uppercase tracking-[0.2em] text-paper-100/80">
            {item.category}
          </span>
          <span className="spec text-[10px] text-paper-100/70">{item.year}</span>
        </div>
      </div>

      <div className={`flex items-center justify-between border-t ${captionRule} p-4`}>
        <div>
          <p className={`font-head text-sm font-700 ${titleText}`}>{item.title}</p>
          <p className={`spec mt-1 text-[11px] ${subText}`}>{item.client}</p>
        </div>
        <span className="h-2.5 w-8 shrink-0" style={{ backgroundColor: item.accent }} aria-hidden />
      </div>
    </article>
  );
}
