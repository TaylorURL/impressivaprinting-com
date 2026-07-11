import { useRef, useEffect, useCallback } from 'react';

// react-bits ClickSpark — a full-viewport canvas overlay that emits a burst of
// radiating sparks wherever the user clicks. Mounted once in the Layout so the
// effect is present on every page.
export default function ClickSpark({
  sparkColor = '#e5352b',
  sparkSize = 11,
  sparkRadius = 22,
  sparkCount = 8,
  duration = 420,
  easing = 'ease-out',
  extraScale = 1,
  children,
}) {
  const canvasRef = useRef(null);
  const sparksRef = useRef([]);
  const rafRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return undefined;
    const parent = canvas.parentElement;
    let resizeTimer;

    const resize = () => {
      const { width, height } = parent.getBoundingClientRect();
      canvas.width = width;
      canvas.height = height;
    };
    const onResize = () => {
      clearTimeout(resizeTimer);
      resizeTimer = setTimeout(resize, 80);
    };
    resize();
    const ro = new ResizeObserver(onResize);
    ro.observe(parent);
    return () => {
      ro.disconnect();
      clearTimeout(resizeTimer);
    };
  }, []);

  const ease = useCallback(
    (t) => {
      if (easing === 'linear') return t;
      if (easing === 'ease-in') return t * t;
      if (easing === 'ease-in-out') return t < 0.5 ? 2 * t * t : -1 + (4 - 2 * t) * t;
      return t * (2 - t); // ease-out
    },
    [easing],
  );

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return undefined;
    const ctx = canvas.getContext('2d');

    const draw = (now) => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      sparksRef.current = sparksRef.current.filter((spark) => {
        const elapsed = now - spark.start;
        if (elapsed >= duration) return false;
        const progress = ease(elapsed / duration);
        const distance = progress * sparkRadius * extraScale;
        const length = sparkSize * (1 - progress);
        const x1 = spark.x + distance * Math.cos(spark.angle);
        const y1 = spark.y + distance * Math.sin(spark.angle);
        const x2 = spark.x + (distance + length) * Math.cos(spark.angle);
        const y2 = spark.y + (distance + length) * Math.sin(spark.angle);
        ctx.strokeStyle = sparkColor;
        ctx.lineWidth = 2;
        ctx.globalAlpha = 1 - progress;
        ctx.beginPath();
        ctx.moveTo(x1, y1);
        ctx.lineTo(x2, y2);
        ctx.stroke();
        return true;
      });
      ctx.globalAlpha = 1;
      rafRef.current = requestAnimationFrame(draw);
    };
    rafRef.current = requestAnimationFrame(draw);
    return () => cancelAnimationFrame(rafRef.current);
  }, [sparkColor, sparkSize, sparkRadius, duration, ease, extraScale]);

  const handleClick = (e) => {
    const reduce = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
    if (reduce) return;
    const rect = canvasRef.current.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    const now = performance.now();
    for (let i = 0; i < sparkCount; i += 1) {
      sparksRef.current.push({
        x,
        y,
        angle: (2 * Math.PI * i) / sparkCount,
        start: now,
      });
    }
  };

  return (
    <div style={{ position: 'relative', width: '100%', height: '100%' }} onClick={handleClick}>
      <canvas
        ref={canvasRef}
        style={{
          position: 'absolute',
          inset: 0,
          pointerEvents: 'none',
          zIndex: 9999,
        }}
      />
      {children}
    </div>
  );
}
