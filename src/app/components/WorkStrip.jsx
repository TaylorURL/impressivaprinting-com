import { Link } from 'react-router-dom';
import { ArrowRight } from 'lucide-react';
import { PORTFOLIO } from '@constants/content.js';
import { ROUTES } from '@constants/routes.js';
import WorkTile from '@components/WorkTile.jsx';

// The section is deliberately 300dvh tall: that extra height is the scroll
// budget the pinned child spends translating the track sideways, read off the
// section's own view timeline. Under reduced motion the section collapses to
// its content and the track scrolls by hand instead.
export default function WorkStrip() {
  const items = PORTFOLIO.slice(0, 6);

  return (
    <section className="work-strip relative h-[300dvh] bg-ink-950">
      <div className="work-strip-pin sticky top-0 flex h-dvh flex-col justify-center overflow-hidden">
        <div className="mx-auto w-full max-w-[1400px] px-5 sm:px-8">
          <div className="flex items-end justify-between border-b border-paper-100/12 pb-4">
            <span className="kicker text-paper-100/50">Recent Work</span>
            <span className="spec hidden items-center gap-2 text-xs text-paper-100/40 sm:flex">
              Scroll to Pan <ArrowRight className="h-3.5 w-3.5" aria-hidden />
            </span>
          </div>
        </div>

        <div className="work-strip-scroll mt-10 overflow-hidden">
          <div className="work-strip-track flex gap-5 pl-5 sm:pl-8">
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
              <span className="spec mt-4 inline-flex items-center gap-2 text-xs uppercase tracking-[0.2em] text-flare">
                Full Portfolio{' '}
                <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" />
              </span>
            </Link>
          </div>
        </div>

        <div className="mx-auto mt-10 w-full max-w-[1400px] px-5 sm:px-8">
          <div className="h-[3px] w-full bg-paper-100/12">
            <div className="work-strip-progress h-full w-full origin-left bg-flare" />
          </div>
        </div>
      </div>
    </section>
  );
}
