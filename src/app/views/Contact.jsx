import { useState } from 'react';
import { Clock, Mail, MapPin, Phone, Send } from 'lucide-react';
import { SITE } from '@constants/site.js';
import Button from '@components/Button.jsx';
import GlassCard from '@components/GlassCard.jsx';
import SectionHeading from '@components/SectionHeading.jsx';

const INPUT =
  'w-full rounded-xl border border-white/15 bg-white/5 px-4 py-3 text-sm text-white placeholder:text-white/35 outline-none transition-colors focus:border-cyan/60 focus:bg-white/[0.07]';

const INFO = [
  { icon: Phone, label: 'Call the Shop', value: SITE.phone, accent: 'text-neon-magenta' },
  { icon: Mail, label: 'Email Us', value: SITE.email, accent: 'text-neon-cyan' },
  { icon: MapPin, label: 'Roll Through', value: SITE.address, accent: 'text-neon-acid' },
  { icon: Clock, label: 'Hours', value: SITE.hours, accent: 'text-sunset' },
];

export default function Contact() {
  const [sent, setSent] = useState(false);

  const handleSubmit = (e) => {
    e.preventDefault();
    // Front-end only: no backend, so we simply confirm receipt in the UI.
    setSent(true);
  };

  return (
    <div className="mx-auto max-w-6xl px-4 pb-6 sm:px-6">
      <SectionHeading kicker="get at us" title="Start The" accent="Conversation" />
      <p className="mt-5 max-w-2xl text-white/60">
        Quotes, questions, rush jobs — send it over. We answer fast during shop hours.
      </p>

      <div className="mt-10 grid gap-6 lg:grid-cols-[1fr_1.2fr]">
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-1">
          {INFO.map((item) => {
            const Icon = item.icon;
            return (
              <GlassCard key={item.label} className="flex items-center gap-4 p-5">
                <span className="grid h-12 w-12 shrink-0 place-items-center rounded-2xl border border-white/10 bg-white/5">
                  <Icon className={`h-5 w-5 ${item.accent}`} strokeWidth={2.2} />
                </span>
                <div>
                  <div className="text-xs uppercase tracking-widest text-white/40">
                    {item.label}
                  </div>
                  <div className="mt-0.5 text-sm font-600 text-white">{item.value}</div>
                </div>
              </GlassCard>
            );
          })}
        </div>

        <GlassCard className="p-7 sm:p-9">
          {sent ? (
            <div className="flex h-full min-h-[20rem] flex-col items-center justify-center text-center">
              <span className="grid h-16 w-16 place-items-center rounded-full street-gradient text-ink-950">
                <Send className="h-7 w-7" />
              </span>
              <h3 className="mt-5 spray text-3xl text-white">Message Slung.</h3>
              <p className="mt-2 max-w-sm text-white/60">
                Thanks for reaching out. This is a demo form — in production it&apos;d land straight
                in the shop inbox. We&apos;d hit you back within one business day.
              </p>
              <Button
                as="button"
                variant="outline"
                size="sm"
                className="mt-6"
                onClick={() => setSent(false)}
              >
                Send Another
              </Button>
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <label className="mb-1.5 block text-xs uppercase tracking-widest text-white/45">
                    Name
                  </label>
                  <input className={INPUT} placeholder="Your name" required />
                </div>
                <div>
                  <label className="mb-1.5 block text-xs uppercase tracking-widest text-white/45">
                    Email
                  </label>
                  <input type="email" className={INPUT} placeholder="you@email.com" required />
                </div>
              </div>
              <div>
                <label className="mb-1.5 block text-xs uppercase tracking-widest text-white/45">
                  What do you need printed?
                </label>
                <input className={INPUT} placeholder="Banners, cards, apparel…" />
              </div>
              <div>
                <label className="mb-1.5 block text-xs uppercase tracking-widest text-white/45">
                  Details
                </label>
                <textarea
                  className={`${INPUT} min-h-[8rem] resize-y`}
                  placeholder="Quantities, sizes, deadline, the vibe…"
                  required
                />
              </div>
              <Button as="button" type="submit" variant="primary" size="lg" full>
                Send It <Send className="h-4 w-4" />
              </Button>
            </form>
          )}
        </GlassCard>
      </div>
    </div>
  );
}
