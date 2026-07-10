import { useMemo, useState } from 'react';
import { ArrowRight } from 'lucide-react';
import {
  QUOTE_FINISHES,
  QUOTE_PRODUCTS,
  QUOTE_QUANTITIES,
  QUOTE_TURNAROUND,
} from '@constants/content.js';
import { ROUTES } from '@constants/routes.js';
import { CONTAINER } from '@constants/ui.js';
import Button from '@components/Button.jsx';
import CountUp from '@components/CountUp.jsx';

function Choice({ active, onClick, children }) {
  return (
    <button
      onClick={onClick}
      className={`spec pressable border px-4 py-2.5 text-xs uppercase tracking-[0.12em] transition-colors ${
        active
          ? 'border-flare bg-flare/10 text-paper-100'
          : 'border-paper-100/15 text-paper-100/55 hover:border-paper-100/40 hover:text-paper-100'
      }`}
    >
      {children}
    </button>
  );
}

export default function QuoteCalculator() {
  const [productId, setProductId] = useState(QUOTE_PRODUCTS[0].id);
  const [qty, setQty] = useState(250);
  const [finishId, setFinishId] = useState('standard');
  const [rushId, setRushId] = useState('standard');

  const product = QUOTE_PRODUCTS.find((p) => p.id === productId);
  const finish = QUOTE_FINISHES.find((f) => f.id === finishId);
  const rush = QUOTE_TURNAROUND.find((t) => t.id === rushId);

  const total = useMemo(() => {
    const raw = product.base * qty * finish.mult * rush.mult;
    // Gentle volume discount to feel real.
    const discount = qty >= 1000 ? 0.85 : qty >= 500 ? 0.92 : 1;
    return Math.round(raw * discount);
  }, [product, qty, finish, rush]);

  return (
    <section className="border-y border-paper-100/10 bg-ink-900">
      <div className={`${CONTAINER} py-20 sm:py-28`}>
        <div className="flex items-end justify-between border-b border-paper-100/12 pb-4">
          <span className="kicker text-flare">Instant Estimate</span>
          <span className="spec hidden text-xs text-paper-100/40 sm:block">Indicative only</span>
        </div>
        <h2 className="display mt-5 text-5xl text-paper-100 sm:text-6xl">Estimate Your Job</h2>

        <div className="mt-12 grid gap-10 lg:grid-cols-[1.3fr_1fr]">
          {/* Controls */}
          <div className="space-y-8">
            <div>
              <span className="kicker mb-3 block text-paper-100/45">01 / Product</span>
              <div className="flex flex-wrap gap-2">
                {QUOTE_PRODUCTS.map((p) => (
                  <Choice key={p.id} active={p.id === productId} onClick={() => setProductId(p.id)}>
                    {p.name}
                  </Choice>
                ))}
              </div>
            </div>
            <div>
              <span className="kicker mb-3 block text-paper-100/45">02 / Quantity</span>
              <div className="flex flex-wrap gap-2">
                {QUOTE_QUANTITIES.map((q) => (
                  <Choice key={q} active={q === qty} onClick={() => setQty(q)}>
                    {q.toLocaleString()}
                  </Choice>
                ))}
              </div>
            </div>
            <div>
              <span className="kicker mb-3 block text-paper-100/45">03 / Finish</span>
              <div className="flex flex-wrap gap-2">
                {QUOTE_FINISHES.map((f) => (
                  <Choice key={f.id} active={f.id === finishId} onClick={() => setFinishId(f.id)}>
                    {f.name}
                  </Choice>
                ))}
              </div>
            </div>
            <div>
              <span className="kicker mb-3 block text-paper-100/45">04 / Turnaround</span>
              <div className="flex flex-wrap gap-2">
                {QUOTE_TURNAROUND.map((t) => (
                  <Choice key={t.id} active={t.id === rushId} onClick={() => setRushId(t.id)}>
                    {t.name}
                  </Choice>
                ))}
              </div>
            </div>
          </div>

          {/* Readout */}
          <div className="flex flex-col justify-between border border-paper-100/12 bg-ink-950 p-8">
            <div>
              <span className="kicker text-paper-100/45">Estimated Total</span>
              <div className="mt-3 flex items-baseline gap-1">
                <span className="display text-6xl text-flare sm:text-7xl">$</span>
                <CountUp
                  key={total}
                  value={String(total)}
                  duration={600}
                  className="display text-6xl text-paper-100 sm:text-7xl"
                />
              </div>
              <p className="spec mt-3 text-xs text-paper-100/45">
                {qty.toLocaleString()} × {product.name} · {finish.name} · {rush.name}
              </p>
              <p className="spec mt-1 text-[11px] text-paper-100/35">
                ≈ ${(total / qty).toFixed(2)} / {product.unit}
              </p>
            </div>

            <div className="mt-8">
              <Button to={ROUTES.contact} variant="flare" size="lg" full>
                Lock In a Real Quote <ArrowRight className="h-4 w-4" />
              </Button>
              <p className="spec mt-3 text-center text-[11px] text-paper-100/35">
                Estimate only — final pricing confirmed on proof.
              </p>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
