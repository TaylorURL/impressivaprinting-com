import { useState } from 'react';
import { ArrowUpRight, Plus } from 'lucide-react';
import { PRODUCTS } from '@constants/products.js';
import { ROUTES } from '@constants/routes.js';
import Button from '@components/Button.jsx';
import Reveal from '@components/Reveal.jsx';
import { ColorBar } from '@components/PrintMarks.jsx';

const WRAP = 'mx-auto max-w-[1400px] px-5 sm:px-8';
const FILTERS = [
  { key: 'all', label: 'All' },
  { key: 'featured', label: 'Best Sellers' },
];

function CatalogRow({ product, index }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="group border-b border-paper-100/12">
      <button
        onClick={() => setOpen((v) => !v)}
        className="grid w-full grid-cols-[auto_1fr_auto] items-center gap-4 py-6 text-left transition-colors duration-300 hover:bg-ink-900 sm:grid-cols-[70px_1fr_180px_140px_auto] sm:gap-6 sm:px-4"
      >
        <span className="spec text-xs tracking-[0.2em] text-paper-100/35">
          {String(index).padStart(2, '0')}
        </span>
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
        <span className="spec hidden text-xs text-paper-100/70 sm:block">
          From ${product.price}
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
      <section className="cropmarks border-b border-paper-100/10 text-paper-100/40">
        <div className={`${WRAP} pb-12 pt-14 sm:pt-20`}>
          <div className="flex items-center justify-between border-b border-paper-100/12 pb-4">
            <span className="kicker text-paper-100/50">No. 002 — Catalog</span>
            <span className="kicker text-paper-100/50">{PRODUCTS.length} Services</span>
          </div>
          <h1 className="display mt-8 text-[17vw] leading-[0.8] text-paper-100 sm:text-8xl">
            Everything <span className="text-flare">We Print</span>
          </h1>
          <p className="mt-6 max-w-xl text-paper-100/60">
            Real stocks, real inks, tight color. Every job proofed before it runs. Figures are
            starting points — tap a line for specs, or request a quote on your exact job.
          </p>
        </div>
        <ColorBar className="h-2" />
      </section>

      <section className={`${WRAP} py-12`}>
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

        <Reveal className="mt-16 grain relative bg-paper-100 p-8 text-ink-950 sm:p-12">
          <div className="flex flex-col items-start justify-between gap-6 sm:flex-row sm:items-center">
            <div>
              <span className="kicker text-flare">Off-Menu</span>
              <h3 className="display mt-3 text-4xl sm:text-5xl">Don&apos;t see your thing?</h3>
              <p className="mt-3 max-w-md text-ink-950/60">
                If it can be printed, we can print it. Send the spec and we&apos;ll quote it.
              </p>
            </div>
            <Button to={ROUTES.contact} variant="flare" size="lg">
              Custom Quote <ArrowUpRight className="h-4 w-4" />
            </Button>
          </div>
        </Reveal>
      </section>
    </>
  );
}
