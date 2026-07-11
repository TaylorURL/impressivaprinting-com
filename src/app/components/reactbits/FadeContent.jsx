import { useEffect, useRef, useState } from 'react';

// react-bits FadeContent — fades (and optionally un-blurs) its children in
// once, when they scroll into view. Dependency-free.
export default function FadeContent({
  children,
  blur = false,
  duration = 800,
  delay = 0,
  threshold = 0.1,
  className = '',
}) {
  const ref = useRef(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return undefined;
    const reduce = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
    if (reduce) {
      setVisible(true);
      return undefined;
    }
    const io = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setTimeout(() => setVisible(true), delay);
          io.disconnect();
        }
      },
      { threshold },
    );
    io.observe(el);
    return () => io.disconnect();
  }, [delay, threshold]);

  return (
    <div
      ref={ref}
      className={className}
      style={{
        opacity: visible ? 1 : 0,
        filter: blur ? (visible ? 'blur(0px)' : 'blur(10px)') : 'none',
        transition: `opacity ${duration}ms ease, filter ${duration}ms ease`,
        willChange: 'opacity, filter',
      }}
    >
      {children}
    </div>
  );
}
