import Reveal from '@components/motion/Reveal.jsx';
import { ColorBar } from '@components/ui/PrintMarks.jsx';

const WRAP = 'mx-auto max-w-[1400px] px-5 sm:px-8';

// The shell every legal page renders into: dark hero, then a narrow prose
// column on paper. `title` and `accent` split the heading so the accent half
// takes the brand red, and `effective` is the date the text took force, which
// is fixed to the wording rather than to the current year.
export default function LegalPage({ kicker, effective, title, accent, intro, children }) {
  return (
    <>
      <section className="skip-offscreen cropmarks border-b border-paper-100/10 bg-ink-950 text-paper-100/40">
        <div className={`${WRAP} pb-12 pt-14 sm:pt-20`}>
          <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-1 border-b border-paper-100/12 pb-4">
            <span className="kicker text-paper-100/50">{kicker}</span>
            <span className="kicker text-paper-100/50">Effective {effective}</span>
          </div>
          <h1 className="display mt-8 text-[16vw] leading-[0.8] text-paper-100 sm:text-8xl">
            {title} <span className="text-flare">{accent}</span>
          </h1>
        </div>
        <ColorBar className="h-2" />
      </section>

      <section className="skip-offscreen relative bg-paper-50 text-ink-950">
        <div className={`relative ${WRAP} max-w-[68ch] space-y-10 py-20 sm:py-28`}>
          <Reveal className="space-y-4 text-lg leading-relaxed text-ink-950/70">
            <p>{intro}</p>
          </Reveal>
          {children}
        </div>
      </section>
    </>
  );
}

export function LegalSection({ title, children }) {
  return (
    <Reveal className="space-y-4">
      <h2 className="display text-3xl text-ink-950">{title}</h2>
      {children}
    </Reveal>
  );
}

export function LegalText({ children }) {
  return <p className="text-base leading-relaxed text-ink-950/70">{children}</p>;
}
