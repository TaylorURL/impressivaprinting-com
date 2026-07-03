import { STATS, SITE } from '@constants/site.js';
import { ROUTES } from '@constants/routes.js';
import Button from '@components/Button.jsx';
import Reveal from '@components/Reveal.jsx';
import SectionHeading from '@components/SectionHeading.jsx';
import { ColorBar } from '@components/PrintMarks.jsx';

const WRAP = 'mx-auto max-w-[1400px] px-5 sm:px-8';

const VALUES = [
  {
    title: 'Bold by Default',
    body: 'We do not do timid. Every job leaves the floor loud, sharp, and impossible to ignore.',
  },
  {
    title: 'Fast When It Counts',
    body: 'Same-day rush on most products. Deadlines are sacred — we hit them, on the dot.',
  },
  {
    title: 'Color on Lock',
    body: 'G7-calibrated presses and hand-checked proofs. What you approve is exactly what you get.',
  },
  {
    title: 'Cleaner Runs',
    body: 'Eco-solvent inks and recyclable stocks wherever the job allows. Loud, not wasteful.',
  },
];

export default function About() {
  return (
    <>
      <section className="cropmarks border-b border-paper-100/10 text-paper-100/40">
        <div className={`${WRAP} pb-12 pt-14 sm:pt-20`}>
          <div className="flex items-center justify-between border-b border-paper-100/12 pb-4">
            <span className="kicker text-paper-100/50">No. 003 — Studio</span>
            <span className="kicker text-paper-100/50">Since Day One</span>
          </div>
          <h1 className="display mt-8 text-[16vw] leading-[0.8] text-paper-100 sm:text-8xl">
            From the <span className="text-flare">Streets Up</span>
          </h1>
        </div>
        <ColorBar className="h-2" />
      </section>

      {/* Story */}
      <section className={`${WRAP} grid gap-12 py-20 sm:py-28 lg:grid-cols-[1.4fr_1fr]`}>
        <Reveal className="space-y-5 text-lg leading-relaxed text-paper-100/70">
          <p>
            Impressiva started in a corner of a warehouse with one press, a stack of blank tees, and
            a refusal to print boring. We came up printing gig posters, crew merch, and storefront
            banners for the block — work that had to look right the first time.
          </p>
          <p>
            Today we run a full floor of pro gear, but the mindset hasn&apos;t moved: treat every
            job like it&apos;s going on the wall of the city. Whether it&apos;s 100 business cards
            or a building-wide banner, it gets the same obsessive eye.
          </p>
          <p className="text-paper-100/90">
            A print shop with a street soul and a modern spine — real craft, real turnaround, no
            corporate stiffness.
          </p>
          <div className="flex flex-wrap gap-3 pt-4">
            <Button to={ROUTES.contact} variant="flare" size="lg">
              Come Through
            </Button>
            <Button to={ROUTES.products} variant="outline" size="lg">
              See the Work
            </Button>
          </div>
        </Reveal>

        <Reveal delay={120} className="self-start border border-paper-100/12">
          {STATS.map((s, i) => (
            <div
              key={s.label}
              className={`flex items-baseline justify-between p-6 ${
                i !== 0 ? 'border-t border-paper-100/12' : ''
              }`}
            >
              <span className="display text-5xl text-flare">{s.value}</span>
              <span className="kicker text-paper-100/45">{s.label}</span>
            </div>
          ))}
          <div className="border-t border-paper-100/12 p-6">
            <span className="spec text-xs text-paper-100/50">{SITE.hours}</span>
          </div>
        </Reveal>
      </section>

      {/* Values on paper */}
      <section className="grain relative bg-paper-100 text-ink-950">
        <div className={`${WRAP} py-20 sm:py-28`}>
          <Reveal>
            <SectionHeading index="—" kicker="The Code" title="What We Stand On" tone="paper" />
          </Reveal>
          <div className="mt-12 grid gap-px border border-ink-950/15 bg-ink-950/15 sm:grid-cols-2 lg:grid-cols-4">
            {VALUES.map((v, i) => (
              <Reveal key={v.title} delay={i * 70} className="bg-paper-100 p-7">
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
