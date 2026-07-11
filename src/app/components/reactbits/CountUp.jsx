import { useEffect, useRef } from 'react';
import { useInView, useMotionValue, useSpring } from 'framer-motion';

// react-bits CountUp — springs a number from `from` to `to` when it scrolls
// into view (and re-runs whenever `to` changes, e.g. the quote estimate).
export default function CountUp({
  to,
  from = 0,
  duration = 1.4,
  className = '',
  separator = ',',
  prefix = '',
  suffix = '',
  decimals = 0,
  startWhen = true,
}) {
  const ref = useRef(null);
  const motionValue = useMotionValue(from);
  const damping = 20 + 40 * (1 / duration);
  const stiffness = 100 * (1 / duration);
  const spring = useSpring(motionValue, { damping, stiffness });
  const inView = useInView(ref, { once: true, margin: '0px' });

  const format = (value) => {
    const fixed = Number(value).toFixed(decimals);
    const [intPart, decPart] = fixed.split('.');
    const grouped = separator
      ? intPart.replace(/\B(?=(\d{3})+(?!\d))/g, separator)
      : intPart;
    return `${prefix}${decPart ? `${grouped}.${decPart}` : grouped}${suffix}`;
  };

  useEffect(() => {
    if (ref.current) ref.current.textContent = format(from);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!inView || !startWhen) return;
    const reduce = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
    if (reduce) {
      spring.jump(to);
      if (ref.current) ref.current.textContent = format(to);
    } else {
      motionValue.set(to);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [inView, startWhen, to]);

  useEffect(() => {
    const unsub = spring.on('change', (latest) => {
      if (ref.current) ref.current.textContent = format(latest);
    });
    return () => unsub();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [spring, decimals, separator, prefix, suffix]);

  return <span ref={ref} className={className} />;
}
