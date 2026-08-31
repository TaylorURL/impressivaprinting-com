import { Check, Ban } from 'lucide-react';
import { ORDER_STATUSES, PIPELINE_STEPS } from '@constants/orders.js';

// The pipeline the shop runs: artwork, review, proof, press, ready, done. A
// canceled order sits outside it, so it gets a notice in place of the rail.
export default function OrderStepper({ status }) {
  const meta = ORDER_STATUSES[status];

  if (!meta || meta.step < 0) {
    return (
      <div className="flex items-center gap-3 border border-paper-100/12 bg-ink-950 px-4 py-3">
        <Ban className="h-4 w-4 shrink-0 text-proc-m" strokeWidth={1.8} />
        <p className="text-xs text-paper-100/55">
          This order was canceled and is no longer in the pipeline.
        </p>
      </div>
    );
  }

  const stage = meta.step;
  return (
    <div className="flex items-center">
      {PIPELINE_STEPS.map((label, i) => {
        const done = i < stage || status === 'completed';
        const active = i === stage && status !== 'completed';
        return (
          <div key={label} className="flex flex-1 items-center last:flex-none">
            <div className="flex flex-col items-center">
              <span
                className={`grid h-6 w-6 place-items-center rounded-full border text-[9px] font-700 transition-colors duration-300 ${
                  done
                    ? 'border-flare bg-flare text-white'
                    : active
                      ? 'border-flare text-flare'
                      : 'border-paper-100/25 text-paper-100/40'
                }`}
              >
                {done ? <Check className="h-3 w-3" strokeWidth={1.8} /> : i + 1}
              </span>
              <span
                className={`spec mt-2 hidden text-[9px] uppercase tracking-[0.1em] sm:block ${
                  done || active ? 'text-paper-100/70' : 'text-paper-100/35'
                }`}
              >
                {label}
              </span>
            </div>
            {i < PIPELINE_STEPS.length - 1 ? (
              <span
                className={`mx-2 h-px flex-1 transition-colors duration-300 ${done ? 'bg-flare' : 'bg-paper-100/15'}`}
              />
            ) : null}
          </div>
        );
      })}
    </div>
  );
}
