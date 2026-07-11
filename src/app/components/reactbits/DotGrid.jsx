import { useEffect, useRef } from 'react';

// react-bits DotGrid — a field of dots that push away from the cursor and
// spring back. Canvas-based; dots glow flare-red near the pointer.
export default function DotGrid({
  dotSize = 3,
  gap = 30,
  baseColor = 'rgba(210, 214, 219, 0.16)',
  activeColor = '#e5352b',
  proximity = 110,
  className = '',
}) {
  const canvasRef = useRef(null);
  const dotsRef = useRef([]);
  const mouseRef = useRef({ x: -9999, y: -9999 });
  const rafRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return undefined;
    const ctx = canvas.getContext('2d');
    const parent = canvas.parentElement;
    const reduce = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;

    const hexToRgb = (hex) => {
      const m = hex.replace('#', '');
      return [
        parseInt(m.substring(0, 2), 16),
        parseInt(m.substring(2, 4), 16),
        parseInt(m.substring(4, 6), 16),
      ];
    };
    const active = hexToRgb(activeColor);

    const build = () => {
      const { width, height } = parent.getBoundingClientRect();
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      canvas.width = width * dpr;
      canvas.height = height * dpr;
      canvas.style.width = `${width}px`;
      canvas.style.height = `${height}px`;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      const cols = Math.floor(width / gap);
      const rows = Math.floor(height / gap);
      const offsetX = (width - (cols - 1) * gap) / 2;
      const offsetY = (height - (rows - 1) * gap) / 2;
      const dots = [];
      for (let i = 0; i < cols; i += 1) {
        for (let j = 0; j < rows; j += 1) {
          const x = offsetX + i * gap;
          const y = offsetY + j * gap;
          dots.push({ x, y, ox: x, oy: y, vx: 0, vy: 0 });
        }
      }
      dotsRef.current = dots;
    };

    const draw = () => {
      const { width, height } = canvas;
      ctx.clearRect(0, 0, width, height);
      const mx = mouseRef.current.x;
      const my = mouseRef.current.y;
      dotsRef.current.forEach((dot) => {
        const dx = dot.x - mx;
        const dy = dot.y - my;
        const dist = Math.hypot(dx, dy);
        if (!reduce && dist < proximity) {
          const force = (1 - dist / proximity) * 14;
          const ang = Math.atan2(dy, dx);
          dot.vx += Math.cos(ang) * force * 0.12;
          dot.vy += Math.sin(ang) * force * 0.12;
        }
        dot.vx += (dot.ox - dot.x) * 0.08;
        dot.vy += (dot.oy - dot.y) * 0.08;
        dot.vx *= 0.82;
        dot.vy *= 0.82;
        dot.x += dot.vx;
        dot.y += dot.vy;

        const glow = Math.max(0, 1 - dist / proximity);
        if (glow > 0 && !reduce) {
          ctx.fillStyle = `rgba(${active[0]}, ${active[1]}, ${active[2]}, ${0.25 + glow * 0.75})`;
        } else {
          ctx.fillStyle = baseColor;
        }
        ctx.beginPath();
        ctx.arc(dot.x, dot.y, dotSize / 2, 0, Math.PI * 2);
        ctx.fill();
      });
      rafRef.current = requestAnimationFrame(draw);
    };

    build();
    draw();

    const ro = new ResizeObserver(build);
    ro.observe(parent);
    const onMove = (e) => {
      const rect = canvas.getBoundingClientRect();
      mouseRef.current = { x: e.clientX - rect.left, y: e.clientY - rect.top };
    };
    const onLeave = () => {
      mouseRef.current = { x: -9999, y: -9999 };
    };
    parent.addEventListener('mousemove', onMove);
    parent.addEventListener('mouseleave', onLeave);

    return () => {
      cancelAnimationFrame(rafRef.current);
      ro.disconnect();
      parent.removeEventListener('mousemove', onMove);
      parent.removeEventListener('mouseleave', onLeave);
    };
  }, [dotSize, gap, baseColor, activeColor, proximity]);

  return <canvas ref={canvasRef} className={`h-full w-full ${className}`} />;
}
