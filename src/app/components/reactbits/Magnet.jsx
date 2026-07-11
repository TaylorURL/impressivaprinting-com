import { useEffect, useRef, useState } from 'react';

// react-bits Magnet — pulls its children toward the cursor when the pointer is
// within a padding radius, then eases them back on leave.
export default function Magnet({
  children,
  padding = 90,
  magnetStrength = 4,
  className = '',
  wrapperClassName = '',
  disabled = false,
  ...rest
}) {
  const ref = useRef(null);
  const [pos, setPos] = useState({ x: 0, y: 0 });

  useEffect(() => {
    if (disabled) {
      setPos({ x: 0, y: 0 });
      return undefined;
    }
    const reduce = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
    if (reduce) return undefined;

    const onMove = (e) => {
      const el = ref.current;
      if (!el) return;
      const rect = el.getBoundingClientRect();
      const cx = rect.left + rect.width / 2;
      const cy = rect.top + rect.height / 2;
      const dx = e.clientX - cx;
      const dy = e.clientY - cy;
      if (Math.abs(dx) < rect.width / 2 + padding && Math.abs(dy) < rect.height / 2 + padding) {
        setPos({ x: dx / magnetStrength, y: dy / magnetStrength });
      } else {
        setPos({ x: 0, y: 0 });
      }
    };
    window.addEventListener('mousemove', onMove);
    return () => window.removeEventListener('mousemove', onMove);
  }, [padding, magnetStrength, disabled]);

  return (
    <div ref={ref} className={wrapperClassName} style={{ display: 'inline-block' }} {...rest}>
      <div
        className={className}
        style={{
          transform: `translate3d(${pos.x}px, ${pos.y}px, 0)`,
          transition: 'transform 0.35s cubic-bezier(0.16, 1, 0.3, 1)',
          willChange: 'transform',
        }}
      >
        {children}
      </div>
    </div>
  );
}
