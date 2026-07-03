import { useState } from 'react';
import { ArrowLeft, ArrowRight, Quote } from 'lucide-react';
import { TESTIMONIALS } from '@constants/content.js';
import SectionHeading from '@components/SectionHeading.jsx';
import Reveal from '@components/Reveal.jsx';

const WRAP = 'mx-auto max-w-[1400px] px-5 sm:px-8';

export default function Testimonials() {
  const [i, setI] = useState(0);
  const t = TESTIMONIALS[i];
  const go = (d) => setI((prev) => (prev + d + TESTIMONIALS.length) % TESTIMONIALS.length);

  return (
    <section className={`${WRAP} py-20 sm:py-28`}>
      <Reveal>
        <SectionHeading index="05" kicker="Testimonials" title="What Clients Say" tone="ink">
          {String(i + 1).padStart(2, '0')} / {String(TESTIMONIALS.length).padStart(2, '0')}
        </SectionHeading>
      </Reveal>

      <Reveal delay={100} className="mt-12 grid gap-8 lg:grid-cols-[1fr_auto] lg:items-end">
        <div>
          <Quote className="h-10 w-10 text-flare" strokeWidth={1.5} />
          <blockquote
            key={t.name}
            className="animate-fade-rise mt-6 max-w-3xl font-head text-2xl font-600 leading-tight text-paper-100 sm:text-3xl md:text-4xl"
          >
            &ldquo;{t.quote}&rdquo;
          </blockquote>
          <div className="mt-8 flex items-center gap-4">
            <span className="h-10 w-10 shrink-0 bg-flare" />
            <div>
              <div className="font-head text-sm font-700 uppercase tracking-wide text-paper-100">
                {t.name}
              </div>
              <div className="spec text-xs text-paper-100/50">
                {t.role} · {t.company}
              </div>
            </div>
          </div>
        </div>

        <div className="flex gap-3">
          <button
            onClick={() => go(-1)}
            className="pressable grid h-12 w-12 place-items-center border border-paper-100/20 text-paper-100/70 hover:border-flare hover:text-flare"
            aria-label="Previous testimonial"
          >
            <ArrowLeft className="h-5 w-5" />
          </button>
          <button
            onClick={() => go(1)}
            className="pressable grid h-12 w-12 place-items-center border border-paper-100/20 text-paper-100/70 hover:border-flare hover:text-flare"
            aria-label="Next testimonial"
          >
            <ArrowRight className="h-5 w-5" />
          </button>
        </div>
      </Reveal>
    </section>
  );
}
