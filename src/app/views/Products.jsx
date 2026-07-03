import { useState } from 'react';
import { motion } from 'framer-motion';
import { ArrowRight, Check } from 'lucide-react';
import { ACCENT_CLASS, PRODUCTS } from '@constants/products.js';
import { ROUTES } from '@constants/routes.js';
import Button from '@components/Button.jsx';
import GlassCard from '@components/GlassCard.jsx';
import SectionHeading from '@components/SectionHeading.jsx';

const FILTERS = [
  { key: 'all', label: 'Everything' },
  { key: 'featured', label: 'Best Sellers' },
];

function ProductRow({ product, index }) {
  const accent = ACCENT_CLASS[product.accent] || ACCENT_CLASS.magenta;
  return (
    <motion.div
      initial={{ opacity: 0, y: 24 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: '-60px' }}
      transition={{ duration: 0.5, delay: (index % 3) * 0.06, ease: [0.23, 1, 0.32, 1] }}
    >
      <GlassCard className={`group h-full p-7 transition-all duration-300 ${accent.ring}`}>
        <div className="flex items-center justify-between">
          <span
            className={`rounded-full border px-3 py-1 text-xs font-700 uppercase tracking-wide ${accent.chip}`}
          >
            {product.tag}
          </span>
          <span className={`h-2.5 w-2.5 rounded-full ${accent.dot}`} />
        </div>

        <h3 className={`mt-5 spray text-4xl leading-none ${accent.text}`}>{product.name}</h3>
        <p className="mt-3 text-sm leading-relaxed text-white/60">{product.blurb}</p>

        <ul className="mt-5 grid grid-cols-2 gap-2">
          {product.details.map((d) => (
            <li key={d} className="flex items-center gap-2 text-xs text-white/60">
              <Check className={`h-3.5 w-3.5 ${accent.text}`} strokeWidth={3} /> {d}
            </li>
          ))}
        </ul>

        <div className="mt-7 flex items-center justify-between border-t border-white/10 pt-5">
          <div>
            <span className="text-xs uppercase tracking-widest text-white/40">Starting at</span>
            <div className="flex items-baseline gap-1">
              <span className="font-head text-2xl font-700 text-white">${product.price}</span>
              <span className="text-xs text-white/50">{product.unit}</span>
            </div>
          </div>
          <Button to={ROUTES.contact} variant="glass" size="sm">
            Get Quote <ArrowRight className="h-4 w-4" />
          </Button>
        </div>
      </GlassCard>
    </motion.div>
  );
}

export default function Products() {
  const [filter, setFilter] = useState('all');
  const list = filter === 'featured' ? PRODUCTS.filter((p) => p.featured) : PRODUCTS;

  return (
    <div className="mx-auto max-w-6xl px-4 pb-6 sm:px-6">
      <SectionHeading kicker="the full catalog" title="Everything We" accent="Print" />
      <p className="mt-5 max-w-2xl text-white/60">
        Real stocks, real inks, tight color. Every job proofed before it runs. Prices shown are
        starting points — hit us for a quote on your exact spec.
      </p>

      <div className="mt-8 flex gap-2">
        {FILTERS.map((f) => (
          <button
            key={f.key}
            onClick={() => setFilter(f.key)}
            className={`pressable rounded-full border px-5 py-2 font-head text-sm font-600 uppercase tracking-wide transition-colors ${
              filter === f.key
                ? 'border-magenta/60 bg-magenta/15 text-white'
                : 'border-white/15 text-white/55 hover:text-white'
            }`}
          >
            {f.label}
          </button>
        ))}
      </div>

      <div className="mt-10 grid gap-5 md:grid-cols-2 lg:grid-cols-3">
        {list.map((product, i) => (
          <ProductRow key={product.id} product={product} index={i} />
        ))}
      </div>

      <GlassCard className="mt-16 flex flex-col items-center justify-between gap-6 p-8 text-center sm:flex-row sm:text-left">
        <div>
          <h3 className="spray text-3xl text-white">Don&apos;t see your thing?</h3>
          <p className="mt-2 text-white/60">If it can be printed, we can print it. Ask us.</p>
        </div>
        <Button to={ROUTES.contact} variant="primary" size="lg">
          Request a Custom Quote <ArrowRight className="h-4 w-4" />
        </Button>
      </GlassCard>
    </div>
  );
}
