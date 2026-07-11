import { useEffect, useRef } from 'react';

// react-bits Squares — an endlessly drifting grid of squares drawn on canvas,
// with a radial vignette. On-brand with the studio's blueprint grid motif.
export default function Squares({
  direction = 'diagonal',
  speed = 0.4,
  borderColor = 'rgba(210, 214, 219, 0.12)',
  squareSize = 44,
  hoverFillColor = 'rgba(229, 53, 43, 0.14)',
  className = '',
}) {
  const canvasRef = useRef(null);
  const offsetRef = useRef({ x: 0, y: 0 });
  const hoverRef = useRef(null);
  const rafRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return undefined;
    const ctx = canvas.getContext('2d');
    const parent = canvas.parentElement;
    const reduce = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;

    const resize = () => {
      const { width, height } = parent.getBoundingClientRect();
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      canvas.width = width * dpr;
      canvas.height = height * dpr;
      canvas.style.width = `${width}px`;
      canvas.style.height = `${height}px`;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };
    resize();
    const ro = new ResizeObserver(resize);
    ro.observe(parent);

    const draw = () => {
      const w = canvas.width;
      const h = canvas.height;
      ctx.clearRect(0, 0, w, h);
      const { x: ox, y: oy } = offsetRef.current;
      const startX = -((ox % squareSize) + squareSize);
      const startY = -((oy % squareSize) + squareSize);

      for (let x = startX; x < w + squareSize; x += squareSize) {
        for (let y = startY; y < h + squareSize; y += squareSize) {
          const gx = Math.floor((x + ox) / squareSize);
          const gy = Math.floor((y + oy) / squareSize);
          if (hoverRef.current && hoverRef.current.x === gx && hoverRef.current.y === gy) {
            ctx.fillStyle = hoverFillColor;
            ctx.fillRect(x, y, squareSize, squareSize);
          }
          ctx.strokeStyle = borderColor;
          ctx.lineWidth = 1;
          ctx.strokeRect(x, y, squareSize, squareSize);
        }
      }

      const grad = ctx.createRadialGradient(
        w / 2,
        h / 2,
        0,
        w / 2,
        h / 2,
        Math.max(w, h) / 1.4,
      );
      grad.addColorStop(0, 'rgba(7,8,10,0)');
      grad.addColorStop(1, 'rgba(7,8,10,0.9)');
      ctx.fillStyle = grad;
      ctx.fillRect(0, 0, w, h);
    };

    const tick = () => {
      if (!reduce) {
        const o = offsetRef.current;
        if (direction === 'right') o.x -= speed;
        else if (direction === 'left') o.x += speed;
        else if (direction === 'up') o.y += speed;
        else if (direction === 'down') o.y -= speed;
        else {
          o.x -= speed;
          o.y -= speed;
        }
      }
      draw();
      rafRef.current = requestAnimationFrame(tick);
    };
    tick();

    const onMove = (e) => {
      const rect = canvas.getBoundingClientRect();
      const { x: ox, y: oy } = offsetRef.current;
      hoverRef.current = {
        x: Math.floor((e.clientX - rect.left + ox) / squareSize),
        y: Math.floor((e.clientY - rect.top + oy) / squareSize),
      };
    };
    const onLeave = () => {
      hoverRef.current = null;
    };
    canvas.addEventListener('mousemove', onMove);
    canvas.addEventListener('mouseleave', onLeave);

    return () => {
      cancelAnimationFrame(rafRef.current);
      ro.disconnect();
      canvas.removeEventListener('mousemove', onMove);
      canvas.removeEventListener('mouseleave', onLeave);
    };
  }, [direction, speed, borderColor, squareSize, hoverFillColor]);

  return <canvas ref={canvasRef} className={`h-full w-full ${className}`} />;
}
