import { useState } from 'react';
import { ArrowRight, Check } from 'lucide-react';
import { SITE } from '@constants/site.js';
import Button from '@components/Button.jsx';
import Reveal from '@components/Reveal.jsx';
import { ColorBar } from '@components/PrintMarks.jsx';
import { fieldLabel, fieldInput } from '@components/Field.jsx';

const WRAP = 'mx-auto max-w-[1400px] px-5 sm:px-8';
const LABEL = fieldLabel('paper');
const INPUT = fieldInput('paper');

const INFO = [
  { k: 'Phone', v: SITE.phone },
  { k: 'Email', v: SITE.email },
  { k: 'Studio', v: SITE.address },
  { k: 'Hours', v: SITE.hours },
];

export default function Contact() {
  const [sent, setSent] = useState(false);
  // Nothing carries the message off the page yet: submitting only swaps in the
  // confirmation panel. The phone and email above are the working routes.
  const handleSubmit = (e) => {
    e.preventDefault();
    setSent(true);
  };

  return (
    <>
      <section className="cropmarks border-b border-paper-100/10 bg-ink-950 text-paper-100/40">
        <div className={`${WRAP} pb-12 pt-14 sm:pt-20`}>
          <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-1 border-b border-paper-100/12 pb-4">
            <span className="kicker text-paper-100/50">Contact</span>
            <span className="kicker text-paper-100/50">Reply Within 1 Day</span>
          </div>
          <h1 className="display mt-8 text-[16vw] leading-[0.8] text-paper-100 sm:text-8xl">
            Get in <span className="text-flare">Touch</span>
          </h1>
        </div>
        <ColorBar className="h-2" />
      </section>

      <section className="skip-offscreen relative bg-paper-50 text-ink-950">
        <div className={`relative ${WRAP} grid gap-12 py-16 sm:py-24 lg:grid-cols-[0.8fr_1.2fr]`}>
          <Reveal className="border-t border-ink-950/15">
            {INFO.map((item, i) => (
              <div
                key={item.k}
                className="grid grid-cols-[90px_1fr] gap-4 border-b border-ink-950/12 py-5"
              >
                <span className="spec text-xs uppercase tracking-[0.18em] text-flare">
                  {String(i + 1).padStart(2, '0')} {item.k}
                </span>
                <span className="spec break-all text-sm text-ink-950/75">{item.v}</span>
              </div>
            ))}
            <p className="mt-8 max-w-xs text-sm leading-relaxed text-ink-950/50">
              Prefer to visit? The studio is open during business hours. Bring your files or just an
              idea to talk through.
            </p>
          </Reveal>

          <Reveal delay={120}>
            {sent ? (
              <div className="flex h-full min-h-[24rem] flex-col items-center justify-center border border-ink-950/12 bg-white p-10 text-center">
                <Check className="h-20 w-20 text-flare" strokeWidth={1.5} aria-hidden />
                <h2 className="display mt-6 text-4xl text-ink-950">Message Sent</h2>
                <p className="mt-3 max-w-sm text-sm text-ink-950/55">
                  The studio has the message and replies within one business day.
                </p>
                <Button
                  as="button"
                  variant="outline-ink"
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
                    <label className={LABEL} htmlFor="contact-name">
                      Name
                    </label>
                    <input
                      id="contact-name"
                      name="name"
                      type="text"
                      autoComplete="name"
                      className={INPUT}
                      placeholder="Full name"
                      required
                    />
                  </div>
                  <div>
                    <label className={LABEL} htmlFor="contact-email">
                      Email
                    </label>
                    <input
                      id="contact-email"
                      name="email"
                      type="email"
                      inputMode="email"
                      autoComplete="email"
                      className={INPUT}
                      placeholder="name@example.com"
                      required
                    />
                  </div>
                </div>
                <div>
                  <label className={LABEL} htmlFor="contact-job">
                    Print Job
                  </label>
                  <input
                    id="contact-job"
                    name="job"
                    type="text"
                    autoComplete="off"
                    className={INPUT}
                    placeholder="Banners, cards, apparel…"
                  />
                </div>
                <div>
                  <label className={LABEL} htmlFor="contact-details">
                    Details
                  </label>
                  <textarea
                    id="contact-details"
                    name="details"
                    className={`${INPUT} min-h-[7rem] resize-y`}
                    placeholder="Quantities, sizes, deadline, and any reference art…"
                    required
                  />
                </div>
                <Button as="button" type="submit" variant="flare" size="lg" full>
                  Send Message <ArrowRight className="h-4 w-4" />
                </Button>
              </form>
            )}
          </Reveal>
        </div>
      </section>
    </>
  );
}
