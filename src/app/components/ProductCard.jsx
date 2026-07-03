import { ArrowUpRight } from 'lucide-react';
import { Link } from 'react-router-dom';
import { ACCENT_CLASS } from '@constants/products.js';
import { ROUTES } from '@constants/routes.js';

export default function ProductCard({ product }) {
  const accent = ACCENT_CLASS[product.accent] || ACCENT_CLASS.magenta;

  return (
    <Link
      to={ROUTES.products}
      className={`glass glass-sheen pressable group relative flex flex-col gap-4 rounded-3xl border-white/10 p-6 transition-all duration-300 ${accent.ring}`}
    >
      <div className="flex items-start justify-between">
        <span
          className={`rounded-full border px-3 py-1 text-xs font-700 uppercase tracking-wide ${accent.chip}`}
        >
          {product.tag}
        </span>
        <ArrowUpRight
          className="h-5 w-5 text-white/40 transition-transform duration-300 ease-street group-hover:-translate-y-0.5 group-hover:translate-x-0.5 group-hover:text-white"
          strokeWidth={2.5}
        />
      </div>

      <div className="mt-2">
        <h3 className={`spray text-3xl leading-none ${accent.text}`}>{product.name}</h3>
        <p className="mt-3 text-sm leading-relaxed text-white/60">{product.blurb}</p>
      </div>

      <div className="mt-auto flex items-end justify-between pt-4">
        <div>
          <span className="text-xs uppercase tracking-widest text-white/40">Starting at</span>
          <div className="flex items-baseline gap-1">
            <span className="font-head text-2xl font-700 text-white">${product.price}</span>
            <span className="text-xs text-white/50">{product.unit}</span>
          </div>
        </div>
        <span className={`h-2.5 w-2.5 rounded-full ${accent.dot} animate-flicker`} />
      </div>
    </Link>
  );
}
