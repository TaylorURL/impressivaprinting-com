import { useState } from 'react';
import { ArrowUpRight, Mail, Phone, Plus } from 'lucide-react';
import { PRODUCTS } from '@constants/products.js';
import { ROUTES } from '@constants/routes.js';
import { SITE } from '@constants/site.js';
import { CONTAINER } from '@constants/ui.js';
import { pad2 } from '@utils/format.js';
import Button from '@components/Button.jsx';
import Reveal from '@components/Reveal.jsx';
import { ColorBar } from '@components/PrintMarks.jsx';
import { SplitText, ShinyText, Squares, GlareHover } from '@reactbits';

const FILTERS = [
  { key: 'all', label: 'All' },
  { key: 'featured', label: 'Best Sellers' },
];

function CatalogRow({ product, index }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="wipe-flare group relative border-b border-paper-100/12">
      <button
        onClick={() => setOpen((v) => !v)}
        className="grid w-full grid-cols-[auto_1fr_auto] items-center gap-4 py-6 pl-3 text-left transition-colors duration-300 hover:bg-ink-900 sm:grid-cols-[70px_1fr_180px_auto] sm:gap-6 sm:px-4"
      >
        <span className="spec text-xs tracking-[0.2em] text-paper-100/35">{pad2(index)}</span>
        <span className="flex items-center gap-3">
          <span
            className="h-3 w-3 shrink-0 rounded-full"
            style={{ backgroundColor: product.swatch }}
          />
          <span className="display text-2xl text-paper-100 transition-colors group-hover:text-flare sm:text-3xl">
            {product.name}
          </span>
        </span>
        <span className="spec hidden text-xs uppercase tracking-[0.15em] text-paper-100/45 sm:block">
          {product.tag}
        </span>
        <Plus
          className={`h-5 w-5 text-paper-100/40 transition-transform duration-300 ease-editorial ${
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
          <div className="grid gap-6 pb-8 sm:grid-cols-[70px_1fr] sm:px-4 lg:grid-cols-[70px_1fr_360px]">
            <span className="spec hidden text-xs text-paper-100/30 sm:block">{product.code}</span>
            <p className="max-w-xl text-sm leading-relaxed text-paper-100/65">{product.blurb}</p>
            <ul className="grid grid-cols-2 gap-x-6 gap-y-2">
              {product.details.map((d) => (
                <li key={d} className="spec flex items-center gap-2 text-xs text-paper-100/55">
                  <span className="h-px w-3 bg-flare" /> {d}
                </li>
              ))}
            </ul>
          </div>
          <div className="pb-8 sm:px-4">
            <Button to={ROUTES.contact} variant="outline" size="sm">
              Request Quote <ArrowUpRight className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function Products() {
  const [filter, setFilter] = useState('all');
  const list = filter === 'featured' ? PRODUCTS.filter((p) => p.featured) : PRODUCTS;

  return (
    <>
      <section className="cropmarks relative overflow-hidden border-b border-paper-100/10 text-paper-100/40">
        {/* react-bits Squares — faint blueprint grid behind the catalog header */}
        <div className="pointer-events-none absolute inset-0 opacity-40">
          <Squares direction="right" speed={0.25} squareSize={52} />
        </div>
        <div className={`relative ${CONTAINER} pb-12 pt-14 sm:pt-20`}>
          <div className="flex items-center justify-between border-b border-paper-100/12 pb-4">
            <span className="kicker text-paper-100/50">No. 002 — Catalog</span>
            <ShinyText text={`${PRODUCTS.length} Services`} className="kicker" speed={5} />
          </div>
          <h1 className="display mt-8 text-[17vw] leading-[0.8] text-paper-100 sm:text-8xl">
            <SplitText text="Everything " splitType="chars" delay={24} />
            <span className="text-flare">
              <SplitText text="We Print" splitType="chars" delay={24} />
            </span>
          </h1>
          <p className="mt-6 max-w-xl text-paper-100/60">
            Real stocks, real inks, tight color. Every job proofed before it runs. Tap a line for
            specs, then call or email for a quote on your exact job.
          </p>
        </div>
        <ColorBar className="h-2" />
      </section>

      <section className={`${CONTAINER} py-12`}>
        <div className="mb-4 flex gap-6">
          {FILTERS.map((f) => (
            <button
              key={f.key}
              onClick={() => setFilter(f.key)}
              className={`spec pressable pb-1 text-xs uppercase tracking-[0.2em] transition-colors ${
                filter === f.key
                  ? 'border-b border-flare text-flare'
                  : 'text-paper-100/50 hover:text-paper-100'
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>

        <div className="border-t border-paper-100/12">
          {list.map((product, i) => (
            <CatalogRow key={product.id} product={product} index={i + 1} />
          ))}
        </div>

        <Reveal className="mt-16">
          <GlareHover
            className="grain relative bg-paper-100 p-8 text-ink-950 sm:p-12"
            glareColor="rgba(229, 53, 43, 0.35)"
          >
            <div className="flex flex-col items-start justify-between gap-6 sm:flex-row sm:items-center">
              <div>
                <span className="kicker text-flare">Off-Menu</span>
                <h3 className="display mt-3 text-4xl sm:text-5xl">Don&apos;t see your thing?</h3>
                <p className="mt-3 max-w-md text-ink-950/60">
                  If it can be printed, we can print it. Send the spec and we&apos;ll quote it.
                </p>
              </div>
              <Button to={ROUTES.contact} variant="flare" size="lg" magnetic>
                Custom Quote <ArrowUpRight className="h-4 w-4" />
              </Button>
            </div>
          </GlareHover>
        </Reveal>
      </section>

      <section className="border-y border-paper-100/10 bg-ink-900">
        <div className={`${CONTAINER} py-20 sm:py-28`}>
          <div className="flex items-end justify-between border-b border-paper-100/12 pb-4">
            <span className="kicker text-flare">Get a Quote</span>
            <span className="spec hidden text-xs text-paper-100/40 sm:block">
              Every job priced to spec
            </span>
          </div>
          <h2 className="display mt-5 text-5xl text-paper-100 sm:text-6xl">
            Call or Email for a Quote
          </h2>
          <p className="mt-5 max-w-xl text-paper-100/60">
            We quote every job by hand. Send your specs, quantities, and deadline and we&apos;ll get
            a number back to you the same day — no two runs are alike, so nothing here is sold at a
            fixed price.
          </p>

          <div className="mt-10 grid gap-px border border-paper-100/12 bg-paper-100/12 sm:grid-cols-2">
            <a
              href={`tel:${SITE.phone.replace(/[^0-9+]/g, '')}`}
              className="group flex items-center justify-between gap-4 bg-ink-950 p-7 transition-colors hover:bg-ink-900"
            >
              <span className="flex items-center gap-4">
                <Phone className="h-6 w-6 shrink-0 text-flare" strokeWidth={1.6} />
                <span>
                  <span className="kicker block text-paper-100/45">Call</span>
                  <span className="display mt-1 block text-2xl text-paper-100">{SITE.phone}</span>
                </span>
              </span>
              <ArrowUpRight className="h-5 w-5 shrink-0 text-paper-100/40 transition-transform duration-300 ease-editorial group-hover:-translate-y-0.5 group-hover:translate-x-0.5 group-hover:text-flare" />
            </a>
            <a
              href={`mailto:${SITE.email}`}
              className="group flex items-center justify-between gap-4 bg-ink-950 p-7 transition-colors hover:bg-ink-900"
            >
              <span className="flex min-w-0 items-center gap-4">
                <Mail className="h-6 w-6 shrink-0 text-flare" strokeWidth={1.6} />
                <span className="min-w-0">
                  <span className="kicker block text-paper-100/45">Email</span>
                  <span className="display mt-1 block break-all text-2xl text-paper-100">
                    {SITE.email}
                  </span>
                </span>
              </span>
              <ArrowUpRight className="h-5 w-5 shrink-0 text-paper-100/40 transition-transform duration-300 ease-editorial group-hover:-translate-y-0.5 group-hover:translate-x-0.5 group-hover:text-flare" />
            </a>
          </div>

          <div className="mt-8">
            <Button to={ROUTES.contact} variant="flare" size="lg" magnetic>
              Send a Quote Request <ArrowUpRight className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </section>
    </>
  );
}
