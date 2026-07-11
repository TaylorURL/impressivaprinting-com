import { useState } from 'react';
import { ArrowRight } from 'lucide-react';
import { CATEGORIES, PORTFOLIO } from '@constants/content.js';
import { ROUTES } from '@constants/routes.js';
import Button from '@components/Button.jsx';
import Reveal from '@components/Reveal.jsx';
import WorkTile from '@components/WorkTile.jsx';
import { ColorBar } from '@components/PrintMarks.jsx';
import { CONTAINER } from '@constants/ui.js';
import { SplitText, ShinyText, DotGrid, GlareHover } from '@reactbits';

export default function Work() {
  const [cat, setCat] = useState('All');
  const list = cat === 'All' ? PORTFOLIO : PORTFOLIO.filter((w) => w.category === cat);

  return (
    <>
      <section className="cropmarks relative overflow-hidden border-b border-paper-100/10 text-paper-100/40">
        {/* react-bits DotGrid — dots scatter from the cursor behind the header */}
        <div className="pointer-events-none absolute inset-0 opacity-70">
          <DotGrid
            dotSize={2.5}
            gap={32}
            baseColor="rgba(210, 214, 219, 0.12)"
            activeColor="#e5352b"
            proximity={110}
          />
        </div>
        <div className={`relative ${CONTAINER} pb-12 pt-14 sm:pt-20`}>
          <div className="flex items-center justify-between border-b border-paper-100/12 pb-4">
            <span className="kicker text-paper-100/50">No. 007 — Portfolio</span>
            <ShinyText text={`${PORTFOLIO.length} Projects`} className="kicker" speed={5} />
          </div>
          <h1 className="display mt-8 text-[16vw] leading-[0.8] text-paper-100 sm:text-8xl">
            <SplitText text="Our " splitType="chars" delay={30} />
            <span className="text-flare">
              <SplitText text="Work" splitType="chars" delay={30} />
            </span>
          </h1>
          <p className="mt-6 max-w-xl text-paper-100/60">
            A selection of recent projects — banners, apparel, cards, and signage produced for
            clients across the city. Printed boldly, built to last.
          </p>
        </div>
        <ColorBar className="h-2" />
      </section>

      <section className={`${CONTAINER} py-12`}>
        <div className="mb-8 flex flex-wrap gap-5">
          {CATEGORIES.map((c) => (
            <button
              key={c}
              onClick={() => setCat(c)}
              className={`spec pressable pb-1 text-xs uppercase tracking-[0.18em] transition-colors ${
                cat === c
                  ? 'border-b border-flare text-flare'
                  : 'text-paper-100/50 hover:text-paper-100'
              }`}
            >
              {c}
            </button>
          ))}
        </div>

        <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {list.map((item, i) => (
            <Reveal key={item.id} delay={(i % 3) * 80}>
              <WorkTile item={item} />
            </Reveal>
          ))}
        </div>

        <Reveal className="mt-16">
          <GlareHover
            className="grain relative bg-paper-100 p-8 text-ink-950 sm:p-12"
            glareColor="rgba(229, 53, 43, 0.35)"
          >
            <div className="flex flex-col items-start justify-between gap-6 sm:flex-row sm:items-center">
              <div>
                <span className="kicker text-flare">Get Started</span>
                <h3 className="display mt-3 text-4xl sm:text-5xl">
                  Let&apos;s make something great.
                </h3>
                <p className="mt-3 max-w-md text-ink-950/60">
                  Every project starts with a file and a deadline. Bring yours and we&apos;ll handle
                  the rest.
                </p>
              </div>
              <Button to={ROUTES.signup} variant="flare" size="lg" magnetic>
                Start a Job <ArrowRight className="h-4 w-4" />
              </Button>
            </div>
          </GlareHover>
        </Reveal>
      </section>
    </>
  );
}
