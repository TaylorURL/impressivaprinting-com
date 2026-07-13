import { Link } from 'react-router-dom';
import { ArrowRight, ArrowUpRight } from 'lucide-react';
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

const WRAP = 'mx-auto max-w-[1400px] px-5 sm:px-8';

const CATEGORIES = [
  {
    id: 'apparel',
    name: 'Apparel',
    blurb: 'DTF, screen, embroidery.',
    image: '/work/impressiva-merch.jpg',
  },
  {
    id: 'business',
    name: 'Business Cards',
    blurb: 'Soft-touch, foil, spot UV.',
    image: '/categories/cat-business-cards.jpg',
  },
  {
    id: 'wide-format',
    name: 'Wide Format',
    blurb: 'Banners, signs, decals.',
    image: '/categories/cat-wide-format.jpg',
  },
  {
    id: 'stickers',
    name: 'Stickers',
    blurb: 'Die-cut, holographic, sheets.',
    image: '/categories/cat-stickers.jpg',
  },
];

function Hero() {
  return (
    <section className="relative overflow-hidden border-b border-paper-100/10 bg-ink-950">
      <div className="blueprint pointer-events-none absolute inset-0 opacity-30" />
      <div
        className={`relative ${WRAP} flex flex-col items-center pb-20 pt-16 text-center sm:pb-28 sm:pt-24`}
      >
        <Reveal>
          <img
            src="/logo.svg"
            alt="Impressiva Printing"
            className="mx-auto w-full max-w-[560px]"
            width="600"
            height="260"
          />
          <p className="mx-auto mt-8 max-w-xl text-lg leading-relaxed text-paper-100/70">
            {SITE.blurb}
          </p>
          <div className="mt-9 flex flex-wrap justify-center gap-3">
            <Button to={ROUTES.products} variant="flare" size="lg">
              Shop Products <ArrowRight className="h-4 w-4" />
            </Button>
            <Button to={ROUTES.contact} variant="outline" size="lg">
              Get a Quote
            </Button>
          </div>
          <div className="mt-8 flex items-center justify-center gap-4">
            <span className="spec text-xs uppercase tracking-[0.2em] text-paper-100/40">Follow</span>
            <SocialIcons
              className="gap-4"
              itemClassName="text-paper-100/60 hover:text-flare"
              iconClassName="h-5 w-5"
            />
          </div>
        </Reveal>
      </div>
      <ColorBar className="h-2" />
    </section>
  );
}

function Featured() {
  return (
    <section className="grain relative bg-paper-100 text-ink-950">
      <div className="halftone-ink pointer-events-none absolute inset-0 opacity-[0.05]" />
      <div className={`relative ${WRAP} py-20 sm:py-24`}>
        <Reveal>
          <SectionHeading index="01" kicker="Featured" title="Best Sellers" tone="paper">
            <Link
              to={ROUTES.products}
              className="inline-flex items-center gap-1 hover:text-flare"
            >
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
    <section className="border-y border-paper-100/10 bg-ink-950">
      <div className={`${WRAP} py-20 sm:py-24`}>
        <Reveal>
          <SectionHeading index="02" kicker="Shop by" title="Categories" tone="ink">
            04 Departments
          </SectionHeading>
        </Reveal>

        <div className="mt-12 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
          {CATEGORIES.map((cat, i) => (
            <Reveal key={cat.id} delay={i * 70}>
              <Link
                to={ROUTES.products}
                className="pressable group relative flex h-full flex-col overflow-hidden border border-paper-100/12 bg-ink-900 transition-colors duration-300 hover:border-flare"
              >
                <div className="relative aspect-[4/3] w-full overflow-hidden bg-ink-950">
                  <img
                    src={cat.image}
                    alt={cat.name}
                    loading="lazy"
                    className="absolute inset-0 h-full w-full object-cover transition-transform duration-700 ease-editorial group-hover:scale-105"
                  />
                  <div className="pointer-events-none absolute inset-x-0 top-0 h-16 bg-gradient-to-b from-ink-950/70 to-transparent" />
                  <span className="absolute left-4 top-4 z-10 spec text-[11px] uppercase tracking-[0.2em] text-paper-100/80">
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
      <div className={`relative ${WRAP} py-20 sm:py-24`}>
        <Reveal>
          <SectionHeading index="03" kicker="Also Available" title="More Products" tone="paper">
            <Link
              to={ROUTES.products}
              className="inline-flex items-center gap-1 hover:text-flare"
            >
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
      <div className={`${WRAP} py-20 sm:py-24`}>
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
    <section className="grain relative bg-paper-100 text-ink-950">
      <div className={`${WRAP} py-20 text-center sm:py-24`}>
        <Reveal>
          <span className="kicker text-flare">Ready to Start?</span>
          <h2 className="display mx-auto mt-6 max-w-4xl text-[14vw] leading-[0.85] sm:text-7xl">
            Let&apos;s Print It.
          </h2>
          <p className="mx-auto mt-6 max-w-md text-ink-950/60">
            Send us your files or a rough idea. We&apos;ll send a proof back the same day and get
            it on press.
          </p>
          <div className="mt-9 flex flex-wrap justify-center gap-3">
            <Button to={ROUTES.contact} variant="flare" size="lg">
              Get a Quote <ArrowRight className="h-4 w-4" />
            </Button>
            <Button to={ROUTES.signup} variant="outline-ink" size="lg">
              Create Account
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
      <Featured />
      <Categories />
      <Catalog />
      <RecentWork />
      <CTA />
    </>
  );
}
