import { TIMELINE } from '@constants/content.js';

// The rail fills as the section travels the viewport and each milestone lifts
// to full strength as it arrives. Both come off view timelines, so the scroll
// position is read by the compositor rather than by React.
export default function Timeline() {
  return (
    <div className="timeline relative mt-12 pl-8 sm:pl-12">
      <div className="absolute bottom-2 left-[9px] top-2 w-px bg-paper-100/15 sm:left-[13px]" />
      <div className="timeline-fill absolute left-[9px] top-2 h-[calc(100%-1rem)] w-px bg-flare sm:left-[13px]" />

      <div className="space-y-12">
        {TIMELINE.map((item) => (
          <div key={item.year} className="timeline-item relative">
            <span className="timeline-dot absolute -left-8 top-1 grid h-[19px] w-[19px] place-items-center rounded-full border border-paper-100/25 bg-ink-950 sm:-left-12">
              <span className="timeline-pip h-px w-2 bg-paper-100/30" />
            </span>
            <div className="timeline-body">
              <span className="display text-4xl text-flare sm:text-5xl">{item.year}</span>
              <h3 className="mt-2 font-head text-xl font-800 uppercase tracking-tight text-paper-100">
                {item.title}
              </h3>
              <p className="mt-2 max-w-lg text-sm leading-relaxed text-paper-100/60">{item.body}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
