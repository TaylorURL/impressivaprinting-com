import useScrollProgress from '@hooks/useScrollProgress.js';
import { TIMELINE } from '@constants/content.js';

// Scroll-scrubbed studio history: a vertical rail fills as you scroll through,
// lighting each milestone as the fill reaches it.
export default function Timeline() {
  const [ref, progress] = useScrollProgress('through');

  return (
    <div ref={ref} className="relative mt-12 pl-8 sm:pl-12">
      {/* Rail */}
      <div className="absolute left-[9px] top-2 bottom-2 w-px bg-paper-100/15 sm:left-[13px]" />
      <div
        className="absolute left-[9px] top-2 w-px bg-flare sm:left-[13px]"
        style={{ height: `calc(${progress * 100}% - 1rem)` }}
      />

      <div className="space-y-12">
        {TIMELINE.map((item, i) => {
          const active = progress >= (i + 0.5) / TIMELINE.length;
          return (
            <div key={item.year} className="relative">
              <span
                className={`absolute -left-8 top-1 grid h-[19px] w-[19px] place-items-center rounded-full border transition-colors duration-300 sm:-left-12 ${
                  active ? 'border-flare bg-flare' : 'border-paper-100/25 bg-ink-950'
                }`}
              >
                <span
                  className={`h-1.5 w-1.5 rounded-full transition-colors ${
                    active ? 'bg-white' : 'bg-paper-100/30'
                  }`}
                />
              </span>
              <div
                className={`transition-all duration-500 ${active ? 'opacity-100' : 'opacity-45'}`}
              >
                <span className="display text-4xl text-flare sm:text-5xl">{item.year}</span>
                <h3 className="mt-2 font-head text-xl font-800 uppercase tracking-tight text-paper-100">
                  {item.title}
                </h3>
                <p className="mt-2 max-w-lg text-sm leading-relaxed text-paper-100/60">
                  {item.body}
                </p>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
