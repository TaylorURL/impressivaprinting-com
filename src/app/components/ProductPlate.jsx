import { Link } from 'react-router-dom';
import { ArrowUpRight } from 'lucide-react';
import { ROUTES } from '@constants/routes.js';
import { pad2 } from '@utils/format.js';

// Editorial product plate: oversized index, SKU chip, Anton name, mono spec row.
// Monochrome by default; flare + swatch reveal on hover. Tone-aware.
export default function ProductPlate({ product, index, tone = 'ink' }) {
  const paper = tone === 'paper';
  const base = paper
    ? 'bg-paper-100 text-ink-950 border-ink-950/15 hover:bg-ink-950 hover:text-paper-100 hover:border-ink-950'
    : 'bg-ink-900 text-paper-100 border-paper-100/12 hover:bg-flare hover:border-flare hover:text-white';
  const dim = paper
    ? 'text-ink-950/50 group-hover:text-paper-100/60'
    : 'text-paper-100/50 group-hover:text-white/70';

  return (
    <Link
      to={ROUTES.products}
      className={`pressable group relative flex flex-col border p-6 transition-[background-color,border-color,transform] duration-300 ease-editorial hover:-translate-y-1 ${base}`}
    >
      <div className="flex items-start justify-between">
        <span className="spec text-xs tracking-[0.2em]">{product.code}</span>
        <span className="flex items-center gap-2">
          <span
            className="h-3 w-3 rounded-full"
            style={{ backgroundColor: product.swatch }}
            aria-hidden
          />
          <ArrowUpRight
            className="h-4 w-4 transition-transform duration-300 ease-editorial group-hover:-translate-y-0.5 group-hover:translate-x-0.5"
            strokeWidth={2}
          />
        </span>
      </div>

      <span className="display mt-10 text-[3.5rem] leading-[0.85] opacity-15 transition-opacity duration-300 group-hover:opacity-40">
        {pad2(index)}
      </span>

      <h3 className="display mt-2 text-3xl">{product.name}</h3>
      <p className={`mt-3 text-sm leading-relaxed ${dim}`}>{product.blurb}</p>

      <div
        className={`mt-6 flex items-center justify-between border-t pt-4 ${paper ? 'border-ink-950/15 group-hover:border-paper-100/20' : 'border-paper-100/12 group-hover:border-white/25'}`}
      >
        <span className="spec text-xs">
          FROM ${product.price}
          <span className={dim}> · {product.unit}</span>
        </span>
        <span className="spec text-xs tracking-[0.2em]">{product.stock}</span>
      </div>
    </Link>
  );
}
