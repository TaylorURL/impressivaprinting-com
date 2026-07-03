import { useEffect, useRef, useState } from 'react';

// Scroll reveal that can never leave content stuck hidden:
// reveals on intersection, immediately if already in view, and via a
// safety timeout as a last resort. Respects reduced-motion.
export default function Reveal({ as = 'div', delay = 0, className = '', children, ...rest }) {
  const Tag = as;
  const ref = useRef(null);
  const [shown, setShown] = useState(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    const reduce = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
    if (reduce) {
      setShown(true);
      return;
    }

    // Already visible at mount (reload mid-page, short pages, last section).
    const rect = el.getBoundingClientRect();
    if (rect.top < window.innerHeight * 1.1) {
      setShown(true);
      return;
    }

    const io = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setShown(true);
          io.disconnect();
        }
      },
      { threshold: 0, rootMargin: '0px 0px -60px 0px' },
    );
    io.observe(el);

    // Absolute fallback — content shows within 1.4s no matter what.
    const safety = setTimeout(() => setShown(true), 1400);

    return () => {
      io.disconnect();
      clearTimeout(safety);
    };
  }, []);

  return (
    <Tag
      ref={ref}
      style={{ transitionDelay: shown ? `${delay}ms` : '0ms' }}
      className={`transition-all duration-700 ease-editorial ${
        shown ? 'translate-y-0 opacity-100' : 'translate-y-5 opacity-0'
      } ${className}`}
      {...rest}
    >
      {children}
    </Tag>
  );
}
