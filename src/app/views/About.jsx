import { motion } from 'framer-motion';
import { Flame, Gauge, PaintBucket, Recycle } from 'lucide-react';
import { STATS, SITE } from '@constants/site.js';
import { ROUTES } from '@constants/routes.js';
import Button from '@components/Button.jsx';
import GlassCard from '@components/GlassCard.jsx';
import SectionHeading from '@components/SectionHeading.jsx';

const VALUES = [
  {
    icon: Flame,
    title: 'Bold By Default',
    body: 'We do not do timid. Every job leaves the shop loud, sharp, and impossible to ignore.',
    accent: 'text-neon-magenta',
  },
  {
    icon: Gauge,
    title: 'Fast When It Counts',
    body: 'Same-day rush on most products. Deadlines are sacred — we hit them.',
    accent: 'text-neon-cyan',
  },
  {
    icon: PaintBucket,
    title: 'Color On Lock',
    body: 'Calibrated presses and hand-checked proofs. What you approve is what you get.',
    accent: 'text-neon-acid',
  },
  {
    icon: Recycle,
    title: 'Cleaner Runs',
    body: 'Eco-solvent inks and recyclable stocks wherever the job allows.',
    accent: 'text-sunset',
  },
];

export default function About() {
  return (
    <div className="mx-auto max-w-6xl px-4 pb-6 sm:px-6">
      <div className="grid gap-10 lg:grid-cols-[1.3fr_1fr] lg:items-center">
        <div>
          <SectionHeading kicker="who we are" title="From The" accent="Streets Up" />
          <div className="mt-6 space-y-4 text-white/65">
            <p>
              Impressiva started in a corner of a warehouse with one press, a stack of blank tees,
              and a refusal to print boring. We came up printing gig posters, crew merch, and
              storefront banners for the block — the kind of work that has to look right the first
              time.
            </p>
            <p>
              Today we run a full floor of pro gear, but the mindset hasn&apos;t moved: treat every
              job like it&apos;s going on the wall of the city. Whether it&apos;s 100 business cards
              or a building-wide banner, it gets the same obsessive eye.
            </p>
            <p>
              We&apos;re a print shop with a street soul and a modern spine — real craft, real
              turnaround, no corporate stiffness.
            </p>
          </div>
          <div className="mt-8 flex flex-wrap gap-4">
            <Button to={ROUTES.contact} variant="primary" size="lg">
              Come Through
            </Button>
            <Button to={ROUTES.products} variant="outline" size="lg">
              See The Work
            </Button>
          </div>
        </div>

        <GlassCard className="relative overflow-hidden p-8">
          <div
            aria-hidden
            className="pointer-events-none absolute -right-10 -top-10 h-48 w-48 rounded-full bg-magenta/30 blur-3xl animate-float-slow"
          />
          <div className="relative grid grid-cols-2 gap-4">
            {STATS.map((s) => (
              <div
                key={s.label}
                className="rounded-2xl border border-white/10 bg-white/5 p-5 text-center"
              >
                <div className="spray text-4xl clip-text street-gradient">{s.value}</div>
                <div className="mt-1 text-xs uppercase tracking-widest text-white/45">
                  {s.label}
                </div>
              </div>
            ))}
          </div>
          <p className="relative mt-6 text-center font-graff text-xl text-neon-cyan rotate-[-1deg]">
            {SITE.hours}
          </p>
        </GlassCard>
      </div>

      <div className="mt-24">
        <SectionHeading kicker="the code" title="What We" accent="Stand On" align="center" />
        <div className="mt-12 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
          {VALUES.map((v, i) => {
            const Icon = v.icon;
            return (
              <motion.div
                key={v.title}
                initial={{ opacity: 0, y: 24 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: '-60px' }}
                transition={{ duration: 0.5, delay: i * 0.07, ease: [0.23, 1, 0.32, 1] }}
              >
                <GlassCard className="h-full p-6">
                  <span className="inline-grid h-12 w-12 place-items-center rounded-2xl border border-white/10 bg-white/5">
                    <Icon className={`h-6 w-6 ${v.accent}`} strokeWidth={2.2} />
                  </span>
                  <h3 className="mt-4 font-head text-lg font-700 text-white">{v.title}</h3>
                  <p className="mt-2 text-sm leading-relaxed text-white/55">{v.body}</p>
                </GlassCard>
              </motion.div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
