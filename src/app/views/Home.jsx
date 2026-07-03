import { motion } from 'framer-motion';
import { ArrowRight, Sparkles, Zap } from 'lucide-react';
import { FEATURED_PRODUCTS } from '@constants/products.js';
import { PROCESS, SITE, STATS } from '@constants/site.js';
import { ROUTES } from '@constants/routes.js';
import Button from '@components/Button.jsx';
import GlassCard from '@components/GlassCard.jsx';
import ProductCard from '@components/ProductCard.jsx';
import SectionHeading from '@components/SectionHeading.jsx';
import Marquee from '@components/Marquee.jsx';

const fadeUp = {
  hidden: { opacity: 0, y: 24 },
  show: (i = 0) => ({
    opacity: 1,
    y: 0,
    transition: { duration: 0.6, delay: i * 0.08, ease: [0.23, 1, 0.32, 1] },
  }),
};

function Hero() {
  return (
    <section className="relative mx-auto max-w-6xl px-4 sm:px-6">
      <div className="relative overflow-hidden rounded-[2rem]">
        <GlassCard className="relative px-6 py-14 sm:px-12 sm:py-20">
          {/* Floating glass blobs */}
          <div
            aria-hidden
            className="pointer-events-none absolute -right-16 -top-20 h-64 w-64 rounded-full bg-magenta/30 blur-3xl animate-float-slow"
          />
          <div
            aria-hidden
            className="pointer-events-none absolute -bottom-24 -left-10 h-64 w-64 rounded-full bg-cyan/25 blur-3xl animate-float-slow [animation-delay:2s]"
          />

          <motion.div
            initial="hidden"
            animate="show"
            variants={fadeUp}
            className="relative max-w-3xl"
          >
            <span className="inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/5 px-4 py-1.5 font-head text-xs font-600 uppercase tracking-widest text-white/70">
              <Sparkles className="h-3.5 w-3.5 text-neon-gold" /> {SITE.address}
            </span>

            <h1 className="mt-6 spray text-6xl leading-[0.85] text-white sm:text-7xl md:text-8xl">
              <span className="block">Print</span>
              <span className="clip-text street-gradient">Loud.</span>
              <span className="mt-2 block font-graff text-4xl normal-case text-neon-cyan rotate-[-2deg] sm:text-5xl">
                Print proud.
              </span>
            </h1>

            <p className="mt-7 max-w-xl text-lg leading-relaxed text-white/65">{SITE.blurb}</p>

            <div className="mt-9 flex flex-wrap items-center gap-4">
              <Button to={ROUTES.products} variant="primary" size="lg">
                Shop the Lineup <ArrowRight className="h-4 w-4" />
              </Button>
              <Button to={ROUTES.signup} variant="glass" size="lg">
                <Zap className="h-4 w-4 text-neon-gold" /> Start a Job
              </Button>
            </div>
          </motion.div>

          {/* Stats strip */}
          <motion.div
            initial="hidden"
            whileInView="show"
            viewport={{ once: true, margin: '-80px' }}
            className="relative mt-14 grid grid-cols-2 gap-4 sm:grid-cols-4"
          >
            {STATS.map((stat, i) => (
              <motion.div key={stat.label} custom={i} variants={fadeUp}>
                <div className="rounded-2xl border border-white/10 bg-white/5 px-4 py-5 text-center backdrop-blur">
                  <div className="spray text-3xl text-white sm:text-4xl">{stat.value}</div>
                  <div className="mt-1 text-xs uppercase tracking-widest text-white/45">
                    {stat.label}
                  </div>
                </div>
              </motion.div>
            ))}
          </motion.div>
        </GlassCard>
      </div>
    </section>
  );
}

function Ticker() {
  return (
    <section className="relative mt-10 border-y border-white/10 bg-white/[0.02] py-5">
      <Marquee
        items={[
          'Business Cards',
          'Vinyl Banners',
          'Custom Apparel',
          'Die-Cut Stickers',
          'Flyers',
          'Storefront Signs',
          'Same-Day Rush',
        ]}
      />
    </section>
  );
}

function Featured() {
  return (
    <section className="mx-auto mt-24 max-w-6xl px-4 sm:px-6">
      <div className="flex flex-col items-start justify-between gap-6 sm:flex-row sm:items-end">
        <SectionHeading kicker="the lineup" title="Primary" accent="products" />
        <Button to={ROUTES.products} variant="outline" size="sm">
          View All <ArrowRight className="h-4 w-4" />
        </Button>
      </div>

      <motion.div
        initial="hidden"
        whileInView="show"
        viewport={{ once: true, margin: '-60px' }}
        className="mt-10 grid gap-5 sm:grid-cols-2 lg:grid-cols-4"
      >
        {FEATURED_PRODUCTS.map((product, i) => (
          <motion.div key={product.id} custom={i} variants={fadeUp}>
            <ProductCard product={product} />
          </motion.div>
        ))}
      </motion.div>
    </section>
  );
}

function Process() {
  return (
    <section className="mx-auto mt-28 max-w-6xl px-4 sm:px-6">
      <SectionHeading
        kicker="how it runs"
        title="Four Steps,"
        accent="Zero Stress"
        align="center"
      />
      <div className="mt-12 grid gap-5 md:grid-cols-2 lg:grid-cols-4">
        {PROCESS.map((item, i) => (
          <motion.div
            key={item.step}
            custom={i}
            variants={fadeUp}
            initial="hidden"
            whileInView="show"
            viewport={{ once: true, margin: '-60px' }}
          >
            <GlassCard className="h-full p-6">
              <span className="spray text-5xl clip-text cyan-gradient">{item.step}</span>
              <h3 className="mt-4 font-head text-xl font-700 text-white">{item.title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-white/55">{item.body}</p>
            </GlassCard>
          </motion.div>
        ))}
      </div>
    </section>
  );
}

function CTA() {
  return (
    <section className="mx-auto mt-28 max-w-6xl px-4 sm:px-6">
      <GlassCard className="relative overflow-hidden px-6 py-14 text-center sm:px-12 sm:py-20">
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0 street-gradient opacity-20 blur-2xl"
        />
        <div className="relative">
          <h2 className="spray text-4xl leading-[0.95] text-white sm:text-6xl">
            Got Art? <span className="clip-text cyan-gradient">Let&apos;s Run It.</span>
          </h2>
          <p className="mx-auto mt-5 max-w-lg text-white/65">
            Make an account, drop your PNG or files, and we&apos;ll have a proof back before you
            finish your coffee.
          </p>
          <div className="mt-8 flex flex-wrap justify-center gap-4">
            <Button to={ROUTES.signup} variant="primary" size="lg">
              Create Account <ArrowRight className="h-4 w-4" />
            </Button>
            <Button to={ROUTES.contact} variant="outline" size="lg">
              Talk to the Shop
            </Button>
          </div>
        </div>
      </GlassCard>
    </section>
  );
}

export default function Home() {
  return (
    <div className="pb-6">
      <Hero />
      <Ticker />
      <Featured />
      <Process />
      <CTA />
    </div>
  );
}
