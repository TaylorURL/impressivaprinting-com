import { useEffect, useRef, useState } from 'react';

// Returns [ref, progress] where progress is 0→1 as the element travels through
// the viewport. `mode` controls the measurement window:
//   'through'  — 0 when the element's top hits the bottom of the viewport,
//                1 when the element's bottom leaves the top (good for parallax).
//   'pin'      — 0→1 across a tall element while its sticky child is pinned
//                (element scrolled from just-entered to about-to-leave).
// Updates are rAF-batched so scroll stays smooth.
export default function useScrollProgress(mode = 'through') {
  const ref = useRef(null);
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    let raf = 0;
    const compute = () => {
      raf = 0;
      const rect = el.getBoundingClientRect();
      const vh = window.innerHeight;
      let p;
      if (mode === 'pin') {
        // Distance scrolled into the tall section over its scrollable travel.
        const travel = rect.height - vh;
        p = travel <= 0 ? 0 : -rect.top / travel;
      } else {
        p = (vh - rect.top) / (vh + rect.height);
      }
      setProgress(Math.min(1, Math.max(0, p)));
    };

    const onScroll = () => {
      if (!raf) raf = requestAnimationFrame(compute);
    };

    compute();
    window.addEventListener('scroll', onScroll, { passive: true });
    window.addEventListener('resize', onScroll, { passive: true });
    return () => {
      window.removeEventListener('scroll', onScroll);
      window.removeEventListener('resize', onScroll);
      if (raf) cancelAnimationFrame(raf);
    };
  }, [mode]);

  return [ref, progress];
}
