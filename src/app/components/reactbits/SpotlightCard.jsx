import { useRef } from 'react';

// react-bits SpotlightCard — a card that reveals a soft radial spotlight
// tracking the cursor. The spotlight color defaults to the flare red.
export default function SpotlightCard({
  children,
  className = '',
  spotlightColor = 'rgba(229, 53, 43, 0.18)',
  ...rest
}) {
  const ref = useRef(null);

  const handleMove = (e) => {
    const el = ref.current;
    if (!el) return;
    const rect = el.getBoundingClientRect();
    el.style.setProperty('--rb-spot-x', `${e.clientX - rect.left}px`);
    el.style.setProperty('--rb-spot-y', `${e.clientY - rect.top}px`);
    el.style.setProperty('--rb-spot-opacity', '1');
  };

  const handleLeave = () => {
    ref.current?.style.setProperty('--rb-spot-opacity', '0');
  };

  return (
    <div
      ref={ref}
      onMouseMove={handleMove}
      onMouseLeave={handleLeave}
      className={`rb-spotlight ${className}`}
      style={{ '--rb-spot-color': spotlightColor }}
      {...rest}
    >
      {children}
    </div>
  );
}
