import { ArrowDownRight, ArrowRight } from 'lucide-react';
import { FEATURED_PRODUCTS } from '@constants/products.js';
import { CAPABILITIES, PROCESS, SITE, STATS } from '@constants/site.js';
import { ROUTES } from '@constants/routes.js';
import Button from '@components/Button.jsx';
import Reveal from '@components/Reveal.jsx';
import Marquee from '@components/Marquee.jsx';
import CountUp from '@components/CountUp.jsx';
import ProductPlate from '@components/ProductPlate.jsx';
import SectionHeading from '@components/SectionHeading.jsx';
import { ColorBar, Registration } from '@components/PrintMarks.jsx';
import LogoMarquee from '@components/LogoMarquee.jsx';
import WorkStrip from '@components/WorkStrip.jsx';
import Testimonials from '@components/Testimonials.jsx';
import Faq from '@components/Faq.jsx';

const WRAP = 'mx-auto max-w-[1400px] px-5 sm:px-8';

function Hero() {
  return (
    <section className="relative cropmarks overflow-hidden border-b border-paper-100/10 text-paper-100/40">
      <div className="blueprint animate-drift pointer-events-none absolute inset-0 -z-0 opacity-60" />
      <div className="scanlines animate-scan pointer-events-none absolute inset-x-0 top-0 -z-0" />
      <div className={`relative ${WRAP} pb-14 pt-14 sm:pb-20 sm:pt-20`}>
        {/* Meta row */}
        <div className="flex items-center justify-between border-b border-paper-100/12 pb-4">
          <span className="kicker text-paper-100/50">No. 001 — Custom Print House</span>
          <span className="hidden kicker text-paper-100/50 sm:block">Est. Bay City</span>
          <Registration className="animate-spin-slow text-flare" />
        </div>

        {/* Headline + deck */}
        <div className="mt-10 grid gap-8 lg:grid-cols-[1.55fr_1fr] lg:items-end">
          <h1 className="display text-paper-100">
            <span className="block text-[19vw] leading-[0.78] sm:text-[15vw] lg:text-[12rem]">
              Print
            </span>
            <span className="animate-glitch block text-[19vw] leading-[0.78] text-flare sm:text-[15vw] lg:text-[12rem]">
              Loud.
            </span>
          </h1>

          <div className="lg:pb-6">
            <p className="max-w-md text-lg leading-relaxed text-paper-100/70">{SITE.blurb}</p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Button to={ROUTES.products} variant="flare" size="lg">
                View Products <ArrowRight className="h-4 w-4" />
              </Button>
              <Button to={ROUTES.signup} variant="outline" size="lg">
                Start a Job
              </Button>
            </div>
          </div>
        </div>

        {/* Spec strip */}
        <div className="mt-14 grid grid-cols-2 border border-paper-100/12 sm:grid-cols-4">
          {STATS.map((s, i) => (
            <div
              key={s.label}
              className={`group p-5 transition-colors duration-300 hover:bg-paper-100/[0.03] ${
                i !== 0 ? 'border-l border-paper-100/12' : ''
              } ${i >= 2 ? 'border-t sm:border-t-0' : ''} ${
                i === 2 ? 'border-t border-paper-100/12' : ''
              }`}
            >
              <CountUp
                value={s.value}
                className="display block text-4xl text-paper-100 transition-colors group-hover:text-flare sm:text-5xl"
              />
              <div className="kicker mt-2 text-paper-100/45">{s.label}</div>
            </div>
          ))}
        </div>
      </div>
      <ColorBar className="animate-bar-pulse h-2" />
    </section>
  );
}

function Ticker() {
  return (
    <section className="border-y border-ink-950/20 bg-flare py-4 text-white">
      <Marquee
        items={[
          'Business Cards',
          'Vinyl Banners',
          'Apparel',
          'Stickers',
          'Signage',
          'Same-Day Rush',
        ]}
        separator="/"
      />
    </section>
  );
}

function Featured() {
  return (
    <section className="grain relative bg-paper-100 text-ink-950">
      <div className="halftone-ink pointer-events-none absolute inset-0 opacity-[0.05]" />
      <div className={`relative ${WRAP} py-20 sm:py-28`}>
        <Reveal>
          <SectionHeading index="02" kicker="Products" title="What We Print" tone="paper">
            08 Services
          </SectionHeading>
        </Reveal>

        <div className="mt-12 grid gap-px border border-ink-950/15 bg-ink-950/15 sm:grid-cols-2 lg:grid-cols-4">
          {FEATURED_PRODUCTS.map((product, i) => (
            <Reveal key={product.id} delay={i * 70}>
              <ProductPlate product={product} index={i + 1} tone="paper" />
            </Reveal>
          ))}
        </div>

        <div className="mt-10 flex justify-end">
          <Button to={ROUTES.products} variant="outline-ink" size="md">
            Full Catalog <ArrowDownRight className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </section>
  );
}

function Process() {
  return (
    <section className={`${WRAP} py-20 sm:py-28`}>
      <Reveal>
        <SectionHeading index="03" kicker="Our Process" title="How It Works" tone="ink">
          Four Steps
        </SectionHeading>
      </Reveal>
      <div className="mt-12 grid gap-px border border-paper-100/12 bg-paper-100/12 md:grid-cols-2 lg:grid-cols-4">
        {PROCESS.map((item, i) => (
          <Reveal key={item.step} delay={i * 70} className="bg-ink-950 p-7">
            <span className="display text-6xl text-flare">{item.step}</span>
            <h3 className="mt-6 font-head text-lg font-800 uppercase tracking-tight text-paper-100">
              {item.title}
            </h3>
            <p className="mt-3 text-sm leading-relaxed text-paper-100/55">{item.body}</p>
          </Reveal>
        ))}
      </div>
    </section>
  );
}

function SpecSheet() {
  return (
    <section className="border-y border-paper-100/10 bg-ink-900">
      <div className={`${WRAP} grid gap-10 py-20 sm:py-24 lg:grid-cols-[0.8fr_1.2fr]`}>
        <Reveal>
          <span className="kicker text-flare">Appendix — Capability</span>
          <h2 className="display mt-5 text-5xl text-paper-100 sm:text-6xl">The Spec Sheet</h2>
          <p className="mt-5 max-w-sm text-sm leading-relaxed text-paper-100/55">
            No guesswork. Here&apos;s exactly what runs on our floor, from stock weights to color
            control — the same sheet we hand production.
          </p>
        </Reveal>
        <Reveal delay={120} className="border-t border-paper-100/15">
          {CAPABILITIES.map((row, i) => (
            <div
              key={row.k}
              className="grid grid-cols-[110px_1fr] gap-4 border-b border-paper-100/12 py-4 sm:grid-cols-[160px_1fr]"
            >
              <span className="spec text-xs uppercase tracking-[0.18em] text-flare">
                {String(i + 1).padStart(2, '0')} {row.k}
              </span>
              <span className="text-sm text-paper-100/75">{row.v}</span>
            </div>
          ))}
        </Reveal>
      </div>
    </section>
  );
}

function CTA() {
  return (
    <section className="grain relative bg-paper-100 text-ink-950">
      <div className={`${WRAP} py-24 text-center sm:py-32`}>
        <Reveal>
          <span className="kicker text-flare">Ready to Start?</span>
          <h2 className="display mx-auto mt-6 max-w-4xl text-[16vw] leading-[0.82] sm:text-8xl">
            Let&apos;s Get Started.
          </h2>
          <p className="mx-auto mt-6 max-w-md text-ink-950/60">
            Create an account, upload your files, and we&apos;ll send a proof back promptly —
            usually the same day.
          </p>
          <div className="mt-9 flex flex-wrap justify-center gap-3">
            <Button to={ROUTES.signup} variant="flare" size="lg">
              Create Account <ArrowRight className="h-4 w-4" />
            </Button>
            <Button to={ROUTES.contact} variant="outline-ink" size="lg">
              Talk to the Shop
            </Button>
          </div>
        </Reveal>
      </div>
    </section>
  );
}

export default function Home() {
  return (
    <>
      <Hero />
      <Ticker />
      <LogoMarquee />
      <Featured />
      <Process />
      <WorkStrip />
      <SpecSheet />
      <Testimonials />
      <Faq />
      <CTA />
    </>
  );
}
