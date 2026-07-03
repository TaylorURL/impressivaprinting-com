import { useEffect, useRef, useState } from 'react';

// Animated counter that runs once when scrolled into view.
// Parses a value like "18K+", "24HR", "99%", "12" into a number + suffix/prefix
// so the odometer feels alive without mangling the label.
function parse(value) {
  const m = String(value).match(/^(\D*)(\d+(?:\.\d+)?)(.*)$/);
  if (!m) return { prefix: '', target: null, suffix: String(value) };
  return { prefix: m[1], target: parseFloat(m[2]), suffix: m[3] };
}

export default function CountUp({ value, duration = 1300, className = '' }) {
  const { prefix, target, suffix } = parse(value);
  const ref = useRef(null);
  const [display, setDisplay] = useState(target === null ? value : `${prefix}0${suffix}`);

  useEffect(() => {
    if (target === null) return;
    const el = ref.current;
    if (!el) return;

    const reduce = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
    if (reduce) {
      setDisplay(value);
      return;
    }

    let raf;
    const run = () => {
      const start = performance.now();
      const decimals = String(target).includes('.') ? 1 : 0;
      const tick = (now) => {
        const t = Math.min((now - start) / duration, 1);
        const eased = 1 - Math.pow(1 - t, 3);
        const current = (target * eased).toFixed(decimals);
        setDisplay(`${prefix}${current}${suffix}`);
        if (t < 1) raf = requestAnimationFrame(tick);
      };
      raf = requestAnimationFrame(tick);
    };

    const io = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          run();
          io.disconnect();
        }
      },
      { threshold: 0.4 },
    );
    io.observe(el);
    return () => {
      io.disconnect();
      cancelAnimationFrame(raf);
    };
  }, [value, target, prefix, suffix, duration]);

  return (
    <span ref={ref} className={className}>
      {display}
    </span>
  );
}
