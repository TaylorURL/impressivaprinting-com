import { useState } from 'react';
import { Plus } from 'lucide-react';
import { FAQS } from '@constants/content.js';
import SectionHeading from '@components/SectionHeading.jsx';
import Reveal from '@components/Reveal.jsx';

const WRAP = 'mx-auto max-w-[1400px] px-5 sm:px-8';

function Item({ faq, index }) {
  const [open, setOpen] = useState(index === 0);
  return (
    <div className="wipe-flare group relative border-b border-paper-100/12">
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center gap-4 py-6 pl-4 pr-2 text-left"
      >
        <span className="spec text-xs text-paper-100/35">{String(index + 1).padStart(2, '0')}</span>
        <span className="flex-1 font-head text-lg font-700 text-paper-100 transition-colors group-hover:text-flare sm:text-xl">
          {faq.q}
        </span>
        <Plus
          className={`h-5 w-5 shrink-0 text-paper-100/40 transition-transform duration-300 ease-editorial ${
            open ? 'rotate-45 text-flare' : ''
          }`}
          strokeWidth={1.6}
        />
      </button>
      <div
        className={`grid overflow-hidden transition-all duration-500 ease-editorial ${
          open ? 'grid-rows-[1fr] opacity-100' : 'grid-rows-[0fr] opacity-0'
        }`}
      >
        <div className="min-h-0">
          <p className="max-w-2xl pb-6 pl-11 pr-6 text-sm leading-relaxed text-paper-100/60">
            {faq.a}
          </p>
        </div>
      </div>
    </div>
  );
}

export default function Faq() {
  return (
    <section className={`${WRAP} py-20 sm:py-28`}>
      <Reveal>
        <SectionHeading index="06" kicker="Before You Ask" title="FAQ" tone="ink">
          {String(FAQS.length).padStart(2, '0')} Answers
        </SectionHeading>
      </Reveal>
      <Reveal delay={100} className="mt-10 border-t border-paper-100/12">
        {FAQS.map((faq, i) => (
          <Item key={faq.q} faq={faq} index={i} />
        ))}
      </Reveal>
    </section>
  );
}
