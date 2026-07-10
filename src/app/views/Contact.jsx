import { useState } from 'react';
import { ArrowRight, Check } from 'lucide-react';
import { SITE } from '@constants/site.js';
import { CONTAINER, FORM_LABEL as LABEL, FORM_INPUT as INPUT } from '@constants/ui.js';
import { pad2 } from '@utils/format.js';
import Button from '@components/Button.jsx';
import Reveal from '@components/Reveal.jsx';
import { ColorBar } from '@components/PrintMarks.jsx';

const INFO = [
  { k: 'Phone', v: SITE.phone },
  { k: 'Email', v: SITE.email },
  { k: 'Studio', v: SITE.address },
  { k: 'Hours', v: SITE.hours },
];

export default function Contact() {
  const [sent, setSent] = useState(false);
  const handleSubmit = (e) => {
    e.preventDefault();
    setSent(true);
  };

  return (
    <>
      <section className="cropmarks border-b border-paper-100/10 text-paper-100/40">
        <div className={`${CONTAINER} pb-12 pt-14 sm:pt-20`}>
          <div className="flex items-center justify-between border-b border-paper-100/12 pb-4">
            <span className="kicker text-paper-100/50">No. 004 — Contact</span>
            <span className="kicker text-paper-100/50">Reply Within 1 Day</span>
          </div>
          <h1 className="display mt-8 text-[16vw] leading-[0.8] text-paper-100 sm:text-8xl">
            Get in <span className="text-flare">Touch</span>
          </h1>
        </div>
        <ColorBar className="h-2" />
      </section>

      <section className={`${CONTAINER} grid gap-12 py-16 sm:py-24 lg:grid-cols-[0.8fr_1.2fr]`}>
        <Reveal className="border-t border-paper-100/15">
          {INFO.map((item, i) => (
            <div
              key={item.k}
              className="grid grid-cols-[90px_1fr] gap-4 border-b border-paper-100/12 py-5"
            >
              <span className="spec text-xs uppercase tracking-[0.18em] text-flare">
                {pad2(i + 1)} {item.k}
              </span>
              <span className="spec break-all text-sm text-paper-100/75">{item.v}</span>
            </div>
          ))}
          <p className="mt-8 max-w-xs text-sm leading-relaxed text-paper-100/50">
            Prefer to visit? The studio is open during business hours — bring your files or just an
            idea to talk through.
          </p>
        </Reveal>

        <Reveal delay={120}>
          {sent ? (
            <div className="flex h-full min-h-[24rem] flex-col items-center justify-center border border-paper-100/12 p-10 text-center">
              <Check className="h-20 w-20 text-flare" strokeWidth={2} aria-hidden />
              <h3 className="display mt-6 text-4xl text-paper-100">Message Sent</h3>
              <p className="mt-3 max-w-sm text-sm text-paper-100/55">
                Thanks for reaching out. This is a demo form — in production it would route directly
                to our studio inbox, and we&apos;d respond within one business day.
              </p>
              <Button
                as="button"
                variant="outline"
                size="sm"
                className="mt-7"
                onClick={() => setSent(false)}
              >
                Send Another
              </Button>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-8">
              <div className="grid gap-8 sm:grid-cols-2">
                <div>
                  <label className={LABEL}>Name</label>
                  <input className={INPUT} placeholder="Your name" required />
                </div>
                <div>
                  <label className={LABEL}>Email</label>
                  <input type="email" className={INPUT} placeholder="you@email.com" required />
                </div>
              </div>
              <div>
                <label className={LABEL}>What do you need printed?</label>
                <input className={INPUT} placeholder="Banners, cards, apparel…" />
              </div>
              <div>
                <label className={LABEL}>Details</label>
                <textarea
                  className={`${INPUT} min-h-[7rem] resize-y`}
                  placeholder="Quantities, sizes, deadline, the vibe…"
                  required
                />
              </div>
              <Button as="button" type="submit" variant="flare" size="lg" full>
                Send It <ArrowRight className="h-4 w-4" />
              </Button>
            </form>
          )}
        </Reveal>
      </section>
    </>
  );
}
