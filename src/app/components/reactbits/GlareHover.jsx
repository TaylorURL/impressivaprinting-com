import { useRef } from 'react';

// react-bits GlareHover — sweeps a soft diagonal glare across its children on
// hover. Purely presentational; wraps existing cards without changing layout.
export default function GlareHover({
  children,
  className = '',
  glareColor = 'rgba(255,255,255,0.35)',
  glareSize = 260,
  transitionDuration = 700,
}) {
  const ref = useRef(null);

  const handleEnter = (e) => {
    const el = ref.current;
    if (!el) return;
    const rect = el.getBoundingClientRect();
    el.style.setProperty('--rb-glare-x', `${e.clientX - rect.left}px`);
    el.style.setProperty('--rb-glare-y', `${e.clientY - rect.top}px`);
    el.style.setProperty('--rb-glare-opacity', '1');
  };
  const handleLeave = () => ref.current?.style.setProperty('--rb-glare-opacity', '0');

  return (
    <div
      ref={ref}
      onMouseEnter={handleEnter}
      onMouseLeave={handleLeave}
      className={`rb-glare ${className}`}
      style={{
        '--rb-glare-color': glareColor,
        '--rb-glare-size': `${glareSize}px`,
        '--rb-glare-duration': `${transitionDuration}ms`,
      }}
    >
      {children}
    </div>
  );
}
