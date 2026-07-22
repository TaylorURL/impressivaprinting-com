import { useState } from 'react';
import { ArrowRight } from 'lucide-react';
import { CATEGORIES, PORTFOLIO } from '@constants/content.js';
import { ROUTES } from '@constants/routes.js';
import Button from '@components/Button.jsx';
import Reveal from '@components/Reveal.jsx';
import WorkTile from '@components/WorkTile.jsx';
import { ColorBar } from '@components/PrintMarks.jsx';

const WRAP = 'mx-auto max-w-[1400px] px-5 sm:px-8';

export default function Work() {
  const [cat, setCat] = useState('All');
  const list = cat === 'All' ? PORTFOLIO : PORTFOLIO.filter((w) => w.category === cat);

  return (
    <>
      {/* Dark masthead */}
      <section className="cropmarks border-b border-paper-100/10 bg-ink-950 text-paper-100/40">
        <div className={`${WRAP} pb-12 pt-14 sm:pt-20`}>
          <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-1 border-b border-paper-100/12 pb-4">
            <span className="kicker text-paper-100/50">No. 007 — Portfolio</span>
            <span className="kicker text-paper-100/50">{PORTFOLIO.length} Projects</span>
          </div>
          <h1 className="display mt-8 text-[16vw] leading-[0.8] text-paper-100 sm:text-8xl">
            Our <span className="text-flare">Work</span>
          </h1>
          <p className="mt-6 max-w-xl text-paper-100/60">
            A selection of recent apparel and custom print work produced for clients across the
            city.
          </p>
        </div>
        <ColorBar className="h-2" />
      </section>

      {/* White gallery */}
      <section className="grain relative bg-paper-50 text-ink-950">
        <div className={`relative ${WRAP} py-12 sm:py-16`}>
          <div className="mb-8 flex flex-wrap gap-5">
            {CATEGORIES.map((c) => (
              <button
                key={c}
                onClick={() => setCat(c)}
                className={`spec pressable pb-1 text-xs uppercase tracking-[0.18em] transition-colors ${
                  cat === c
                    ? 'border-b border-flare text-flare'
                    : 'text-ink-950/50 hover:text-ink-950'
                }`}
              >
                {c}
              </button>
            ))}
          </div>

          <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
            {list.map((item, i) => (
              <Reveal key={item.id} delay={(i % 3) * 80}>
                <WorkTile item={item} tone="paper" />
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      {/* Dark CTA */}
      <section className="border-t border-paper-100/10 bg-ink-950">
        <div className={`${WRAP} py-20 sm:py-24`}>
          <Reveal className="flex flex-col items-start justify-between gap-6 sm:flex-row sm:items-center">
            <div>
              <span className="kicker text-flare">Get Started</span>
              <h3 className="display mt-3 text-4xl text-paper-100 sm:text-5xl">
                Have a project in mind?
              </h3>
              <p className="mt-3 max-w-md text-paper-100/60">
                Every project starts with a file and a deadline. Send yours and we&apos;ll handle
                the rest.
              </p>
            </div>
            <Button to={ROUTES.signup} variant="flare" size="lg">
              Start a Job <ArrowRight className="h-4 w-4" />
            </Button>
          </Reveal>
        </div>
      </section>
    </>
  );
}
