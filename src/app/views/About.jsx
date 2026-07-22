import { STATS, SITE } from '@constants/site.js';
import { ROUTES } from '@constants/routes.js';
import Button from '@components/Button.jsx';
import Reveal from '@components/Reveal.jsx';
import CountUp from '@components/CountUp.jsx';
import Timeline from '@components/Timeline.jsx';
import SectionHeading from '@components/SectionHeading.jsx';
import { ColorBar } from '@components/PrintMarks.jsx';

const WRAP = 'mx-auto max-w-[1400px] px-5 sm:px-8';

const VALUES = [
  {
    title: 'Bold by Default',
    body: 'Every job leaves the floor sharp, saturated, and impossible to ignore.',
  },
  {
    title: 'Fast When It Counts',
    body: 'Same-day rush on most products. We treat your deadline as the deliverable.',
  },
  {
    title: 'Color, Controlled',
    body: 'G7-calibrated presses and hand-checked proofs. What you approve is exactly what you get.',
  },
  {
    title: 'Cleaner Runs',
    body: 'Eco-solvent inks and recyclable stocks wherever the job allows.',
  },
];

export default function About() {
  return (
    <>
      {/* Dark masthead */}
      <section className="cropmarks border-b border-paper-100/10 bg-ink-950 text-paper-100/40">
        <div className={`${WRAP} pb-12 pt-14 sm:pt-20`}>
          <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-1 border-b border-paper-100/12 pb-4">
            <span className="kicker text-paper-100/50">No. 003 — Studio</span>
            <span className="kicker text-paper-100/50">Since Day One</span>
          </div>
          <h1 className="display mt-8 text-[16vw] leading-[0.8] text-paper-100 sm:text-8xl">
            Our <span className="text-flare">Story</span>
          </h1>
        </div>
        <ColorBar className="h-2" />
      </section>

      {/* White story */}
      <section className="grain relative bg-paper-50 text-ink-950">
        <div className={`relative ${WRAP} grid gap-12 py-20 sm:py-28 lg:grid-cols-[1.4fr_1fr]`}>
          <Reveal className="space-y-5 text-lg leading-relaxed text-ink-950/70">
            <p>
              Impressiva began in a single warehouse room with one press and a simple standard:
              never print anything forgettable. Early work — event posters, custom apparel, and
              storefront banners for local businesses — had to be right the first time, every time.
            </p>
            <p>
              Today we operate a full production floor, but the approach hasn&apos;t changed. Every
              job gets the same attention to detail, whether it&apos;s 100 business cards or a
              building-wide banner.
            </p>
            <p className="font-medium text-ink-950">
              Bold creative work backed by disciplined craft — dependable turnaround, consistent
              color, and a team that treats your deadline as its own.
            </p>
            <div className="flex flex-wrap gap-3 pt-4">
              <Button to={ROUTES.contact} variant="flare" size="lg">
                Get in Touch
              </Button>
              <Button to={ROUTES.work} variant="outline-ink" size="lg">
                View Our Work
              </Button>
            </div>
          </Reveal>

          <Reveal delay={120} className="self-start border border-ink-950/12">
            {STATS.map((s, i) => (
              <div
                key={s.label}
                className={`flex items-baseline justify-between p-6 ${
                  i !== 0 ? 'border-t border-ink-950/12' : ''
                }`}
              >
                <CountUp value={s.value} className="display text-5xl text-flare" />
                <span className="kicker text-ink-950/45">{s.label}</span>
              </div>
            ))}
            <div className="border-t border-ink-950/12 p-6">
              <span className="spec text-xs text-ink-950/50">{SITE.hours}</span>
            </div>
          </Reveal>
        </div>
      </section>

      {/* Dark scroll-scrubbed history */}
      <section className="border-t border-paper-100/10 bg-ink-900">
        <div className={`${WRAP} py-20 sm:py-28`}>
          <Reveal>
            <SectionHeading index="—" kicker="The Timeline" title="How We Got Here" tone="ink" />
          </Reveal>
          <Timeline />
        </div>
      </section>

      {/* White values */}
      <section className="grain relative bg-paper-50 text-ink-950">
        <div className={`relative ${WRAP} py-20 sm:py-28`}>
          <Reveal>
            <SectionHeading index="—" kicker="Our Standards" title="What We Stand For" tone="paper" />
          </Reveal>
          <div className="mt-12 grid gap-px border border-ink-950/12 bg-ink-950/12 sm:grid-cols-2 lg:grid-cols-4">
            {VALUES.map((v, i) => (
              <Reveal key={v.title} delay={i * 70} className="bg-paper-50 p-7">
                <span className="display text-5xl text-ink-950/15">
                  {String(i + 1).padStart(2, '0')}
                </span>
                <h3 className="mt-5 font-head text-lg font-800 uppercase tracking-tight text-ink-950">
                  {v.title}
                </h3>
                <p className="mt-3 text-sm leading-relaxed text-ink-950/60">{v.body}</p>
              </Reveal>
            ))}
          </div>
        </div>
      </section>
    </>
  );
}
