import { Link } from 'react-router-dom';
import { ArrowRight, ArrowUpRight, Mail, Phone } from 'lucide-react';
import { FEATURED_PRODUCTS, PRODUCTS } from '@constants/products.js';
import { PORTFOLIO } from '@constants/content.js';
import { SITE } from '@constants/site.js';
import { ROUTES } from '@constants/routes.js';
import Button from '@components/Button.jsx';
import Reveal from '@components/Reveal.jsx';
import ProductPlate from '@components/ProductPlate.jsx';
import SectionHeading from '@components/SectionHeading.jsx';
import WorkTile from '@components/WorkTile.jsx';
import SocialIcons from '@components/SocialIcons.jsx';
import { ColorBar } from '@components/PrintMarks.jsx';
import { CONTAINER } from '@constants/ui.js';
import {
  BlurText,
  RotatingText,
  CountUp,
  SplitText,
  Threads,
  DotGrid,
  Squares,
  SpotlightCard,
} from '@reactbits';

const CATEGORIES = [
  {
    id: 'business',
    name: 'Business Cards',
    blurb: 'Soft-touch, foil, spot UV.',
    accent: '#e5352b',
  },
  {
    id: 'apparel',
    name: 'Apparel',
    blurb: 'DTF, screen, embroidery.',
    accent: '#2f6bff',
  },
  {
    id: 'wide-format',
    name: 'Wide Format',
    blurb: 'Banners, signs, decals.',
    accent: '#1E7A85',
  },
  {
    id: 'stickers',
    name: 'Stickers',
    blurb: 'Die-cut, holographic, sheets.',
    accent: '#b81f16',
  },
];

const HERO_STATS = [
  { k: 'Turnaround', to: 24, suffix: 'hr', tail: 'Rush' },
  { k: 'Presses', to: 12, suffix: '', tail: 'On-Site' },
  { k: 'Jobs Shipped', to: 18, suffix: 'K+', tail: '' },
  { k: 'Repeat Clients', to: 99, suffix: '%', tail: '' },
];

function Hero() {
  return (
    <section className="relative overflow-hidden border-b border-paper-100/10 bg-ink-950">
      <div className="blueprint pointer-events-none absolute inset-0 opacity-40" />
      {/* react-bits Threads — flowing WebGL line accent behind the hero */}
      <div className="pointer-events-none absolute inset-0 opacity-[0.55]">
        <Threads color="#e5352b" amplitude={1.1} distance={0.5} />
      </div>
      <div className={`relative ${CONTAINER} pb-16 pt-12 sm:pb-24 sm:pt-16`}>
        <div className="grid gap-10 lg:grid-cols-[1.1fr_1fr] lg:items-center">
          <Reveal>
            <img
              src="/logo.svg"
              alt="Impressiva Printing"
              className="w-full max-w-[640px]"
              width="600"
              height="260"
            />
            <BlurText
              as="p"
              text={SITE.blurb}
              className="mt-8 max-w-lg text-lg leading-relaxed text-paper-100/70"
              delay={40}
            />
            <div className="mt-6 flex items-center gap-3">
              <span className="kicker text-flare">We Print</span>
              <RotatingText
                texts={['Business Cards', 'Vinyl Banners', 'Custom Apparel', 'Stickers', 'Signage']}
                mainClassName="font-head text-lg font-800 uppercase tracking-tight text-paper-100"
                rotationInterval={2000}
              />
            </div>
            <div className="mt-8 flex flex-wrap gap-3">
              <Button to={ROUTES.contact} variant="flare" size="lg" magnetic>
                Get a Quote <ArrowRight className="h-4 w-4" />
              </Button>
              <Button to={ROUTES.products} variant="outline" size="lg" magnetic>
                View Products
              </Button>
            </div>
            <div className="mt-8 flex items-center gap-4">
              <span className="spec text-xs uppercase tracking-[0.2em] text-paper-100/40">
                Follow
              </span>
              <SocialIcons
                className="gap-4"
                itemClassName="text-paper-100/60 hover:text-flare"
                iconClassName="h-5 w-5"
              />
            </div>
          </Reveal>

          <Reveal delay={120}>
            <div className="grid grid-cols-2 gap-px border border-paper-100/12 bg-paper-100/12">
              {HERO_STATS.map((s) => (
                <div key={s.k} className="bg-ink-900 p-6">
                  <div className="kicker text-paper-100/45">{s.k}</div>
                  <div className="display mt-3 text-4xl text-paper-100 sm:text-5xl">
                    <CountUp to={s.to} suffix={s.suffix} separator="" />
                    {s.tail ? (
                      <span className="ml-2 align-middle text-lg text-paper-100/55 sm:text-xl">
                        {s.tail}
                      </span>
                    ) : null}
                  </div>
                </div>
              ))}
            </div>
          </Reveal>
        </div>
      </div>
      <ColorBar className="h-2" />
    </section>
  );
}

function Featured() {
  return (
    <section className="grain relative bg-paper-100 text-ink-950">
      <div className="halftone-ink pointer-events-none absolute inset-0 opacity-[0.05]" />
      <div className={`relative ${CONTAINER} py-20 sm:py-24`}>
        <Reveal>
          <SectionHeading index="01" kicker="Featured" title="Best Sellers" tone="paper">
            <Link to={ROUTES.products} className="inline-flex items-center gap-1 hover:text-flare">
              View all <ArrowUpRight className="h-3.5 w-3.5" />
            </Link>
          </SectionHeading>
        </Reveal>

        <div className="mt-12 grid gap-px border border-ink-950/15 bg-ink-950/15 sm:grid-cols-2 lg:grid-cols-4">
          {FEATURED_PRODUCTS.map((product, i) => (
            <Reveal key={product.id} delay={i * 60}>
              <ProductPlate product={product} index={i + 1} tone="paper" />
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}

function Categories() {
  return (
    <section className="relative overflow-hidden border-y border-paper-100/10 bg-ink-950">
      {/* react-bits Squares — drifting blueprint grid behind the departments */}
      <div className="pointer-events-none absolute inset-0 opacity-60">
        <Squares direction="diagonal" speed={0.3} squareSize={46} />
      </div>
      <div className={`relative ${CONTAINER} py-20 sm:py-24`}>
        <Reveal>
          <SectionHeading index="02" kicker="Browse by" title="Categories" tone="ink">
            04 Departments
          </SectionHeading>
        </Reveal>

        <div className="mt-12 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
          {CATEGORIES.map((cat, i) => (
            <Reveal key={cat.id} delay={i * 70}>
              <SpotlightCard className="h-full" spotlightColor="rgba(229, 53, 43, 0.2)">
                <Link
                  to={ROUTES.products}
                  className="pressable group relative flex h-full flex-col overflow-hidden border border-paper-100/12 bg-ink-900 transition-colors duration-300 hover:border-flare"
                >
                <div className="relative aspect-[4/3] w-full overflow-hidden">
                  <div
                    className="absolute inset-0 transition-transform duration-700 ease-editorial group-hover:scale-105"
                    style={{ backgroundColor: cat.accent }}
                  />
                  <div className="halftone-ink pointer-events-none absolute inset-0 opacity-[0.15]" />
                  <div
                    className="absolute inset-0 opacity-90"
                    style={{
                      backgroundImage: `repeating-linear-gradient(-45deg, rgba(7,8,10,0) 0, rgba(7,8,10,0) 22px, rgba(7,8,10,0.16) 22px, rgba(7,8,10,0.16) 24px)`,
                    }}
                  />
                  <span className="absolute left-4 top-4 spec text-[11px] uppercase tracking-[0.2em] text-ink-950/70">
                    0{i + 1}
                  </span>
                </div>
                <div className="flex items-center justify-between border-t border-paper-100/12 p-5">
                  <div>
                    <h3 className="font-head text-lg font-800 uppercase tracking-tight text-paper-100">
                      {cat.name}
                    </h3>
                    <p className="spec mt-1 text-[11px] text-paper-100/50">{cat.blurb}</p>
                  </div>
                  <ArrowUpRight
                    className="h-5 w-5 text-paper-100/40 transition-all duration-300 ease-editorial group-hover:-translate-y-0.5 group-hover:translate-x-0.5 group-hover:text-flare"
                    strokeWidth={2}
                  />
                </div>
                </Link>
              </SpotlightCard>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}

function Catalog() {
  const rest = PRODUCTS.filter((p) => !p.featured);
  return (
    <section className="grain relative bg-paper-100 text-ink-950">
      <div className={`relative ${CONTAINER} py-20 sm:py-24`}>
        <Reveal>
          <SectionHeading index="03" kicker="Also Available" title="More Products" tone="paper">
            <Link to={ROUTES.products} className="inline-flex items-center gap-1 hover:text-flare">
              Full catalog <ArrowUpRight className="h-3.5 w-3.5" />
            </Link>
          </SectionHeading>
        </Reveal>

        <div className="mt-12 grid gap-px border border-ink-950/15 bg-ink-950/15 sm:grid-cols-2 lg:grid-cols-4">
          {rest.map((product, i) => (
            <Reveal key={product.id} delay={i * 60}>
              <ProductPlate
                product={product}
                index={FEATURED_PRODUCTS.length + i + 1}
                tone="paper"
              />
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}

function RecentWork() {
  const items = PORTFOLIO.slice(0, 3);
  return (
    <section className="bg-ink-950">
      <div className={`${CONTAINER} py-20 sm:py-24`}>
        <Reveal>
          <SectionHeading index="04" kicker="Portfolio" title="Recent Work" tone="ink">
            <Link to={ROUTES.work} className="inline-flex items-center gap-1 hover:text-flare">
              See more <ArrowUpRight className="h-3.5 w-3.5" />
            </Link>
          </SectionHeading>
        </Reveal>

        <div className="mt-12 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {items.map((item, i) => (
            <Reveal key={item.id} delay={i * 80}>
              <WorkTile item={item} />
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  );
}

function CTA() {
  return (
    <section className="grain relative overflow-hidden bg-paper-100 text-ink-950">
      {/* react-bits DotGrid — dots scatter from the cursor across the CTA */}
      <div className="pointer-events-none absolute inset-0 opacity-70">
        <DotGrid
          dotSize={3}
          gap={34}
          baseColor="rgba(14, 16, 19, 0.14)"
          activeColor="#e5352b"
          proximity={120}
        />
      </div>
      <div className={`relative ${CONTAINER} py-20 text-center sm:py-24`}>
        <Reveal>
          <span className="kicker text-flare">Ready to Start?</span>
          <h2 className="display mx-auto mt-6 max-w-4xl text-[14vw] leading-[0.85] sm:text-7xl">
            <SplitText text="Let's Print It." splitType="chars" delay={34} duration={0.7} />
          </h2>
          <p className="mx-auto mt-6 max-w-md text-ink-950/60">
            Every job is quoted to spec — no fixed prices, no online cart. Send your files or a
            rough idea and we&apos;ll get a proof and a quote back the same day.
          </p>
          <div className="mt-9 flex flex-wrap justify-center gap-3">
            <Button to={ROUTES.contact} variant="flare" size="lg" magnetic>
              Get a Quote <ArrowRight className="h-4 w-4" />
            </Button>
            <Button to={ROUTES.signup} variant="outline-ink" size="lg" magnetic>
              Create Account
            </Button>
          </div>
          <div className="spec mt-8 flex flex-wrap items-center justify-center gap-x-8 gap-y-3 text-sm text-ink-950/70">
            <a
              href={`tel:${SITE.phone.replace(/[^0-9+]/g, '')}`}
              className="inline-flex items-center gap-2 transition-colors hover:text-flare"
            >
              <Phone className="h-4 w-4" strokeWidth={1.8} /> {SITE.phone}
            </a>
            <a
              href={`mailto:${SITE.email}`}
              className="inline-flex items-center gap-2 break-all transition-colors hover:text-flare"
            >
              <Mail className="h-4 w-4" strokeWidth={1.8} /> {SITE.email}
            </a>
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
      <Featured />
      <Categories />
      <Catalog />
      <RecentWork />
      <CTA />
    </>
  );
}
