import { Link } from 'react-router-dom';
import { ArrowRight } from 'lucide-react';
import useScrollProgress from '@hooks/useScrollProgress.js';
import { PORTFOLIO } from '@constants/content.js';
import { ROUTES } from '@constants/routes.js';
import WorkTile from '@components/WorkTile.jsx';

// Scroll-controlled horizontal gallery. Vertical scroll through the tall
// section drives the horizontal track; a sticky child stays pinned meanwhile.
export default function WorkStrip() {
  const [ref, progress] = useScrollProgress('pin');
  const items = PORTFOLIO.slice(0, 6);
  // Track shifts left by ~55% of its own width across the scroll window.
  const shift = progress * 55;

  return (
    <section ref={ref} className="relative h-[300vh] bg-ink-950">
      <div className="sticky top-0 flex h-screen flex-col justify-center overflow-hidden">
        <div className="mx-auto w-full max-w-[1400px] px-5 sm:px-8">
          <div className="flex items-end justify-between border-b border-paper-100/12 pb-4">
            <span className="kicker text-paper-100/50">
              <span className="text-flare">04</span> / Recent Work
            </span>
            <span className="spec hidden items-center gap-1.5 text-xs text-paper-100/40 sm:flex">
              Scroll to pan <ArrowRight className="h-3.5 w-3.5" aria-hidden />
            </span>
          </div>
        </div>

        <div className="mt-10 overflow-hidden">
          <div
            className="flex gap-5 pl-5 sm:pl-8"
            style={{ transform: `translate3d(-${shift}%, 0, 0)` }}
          >
            {items.map((item) => (
              <WorkTile
                key={item.id}
                item={item}
                className="w-[78vw] shrink-0 sm:w-[42vw] lg:w-[30vw]"
              />
            ))}
            <Link
              to={ROUTES.work}
              className="group flex w-[78vw] shrink-0 flex-col items-center justify-center border border-dashed border-paper-100/20 bg-ink-900 text-center sm:w-[42vw] lg:w-[24vw]"
            >
              <span className="display text-5xl text-paper-100">View All</span>
              <span className="mt-4 inline-flex items-center gap-2 spec text-xs uppercase tracking-[0.2em] text-flare">
                Full Portfolio{' '}
                <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" />
              </span>
            </Link>
          </div>
        </div>

        {/* Scrub progress bar */}
        <div className="mx-auto mt-10 w-full max-w-[1400px] px-5 sm:px-8">
          <div className="h-[3px] w-full bg-paper-100/12">
            <div className="h-full bg-flare" style={{ width: `${progress * 100}%` }} />
          </div>
        </div>
      </div>
    </section>
  );
}
