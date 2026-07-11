import { useEffect, useRef } from 'react';

// react-bits LetterGlitch — a matrix of characters that randomly re-roll and
// flicker between colors. Tuned to the flare/steel duotone for the print shop.
export default function LetterGlitch({
  glitchColors = ['#272c33', '#b81f16', '#e5352b'],
  glitchSpeed = 60,
  characters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789@#$%&*+=/',
  className = '',
  fontSize = 16,
  smooth = true,
}) {
  const canvasRef = useRef(null);
  const lettersRef = useRef([]);
  const gridRef = useRef({ cols: 0, rows: 0 });
  const rafRef = useRef(null);
  const lastRef = useRef(0);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return undefined;
    const ctx = canvas.getContext('2d');
    const parent = canvas.parentElement;
    const chars = characters.split('');
    const reduce = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;

    const rand = (arr) => arr[Math.floor(Math.random() * arr.length)];
    const charWidth = fontSize * 0.62;
    const charHeight = fontSize * 1.1;

    const build = () => {
      const { width, height } = parent.getBoundingClientRect();
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      canvas.width = width * dpr;
      canvas.height = height * dpr;
      canvas.style.width = `${width}px`;
      canvas.style.height = `${height}px`;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      const cols = Math.ceil(width / charWidth);
      const rows = Math.ceil(height / charHeight);
      gridRef.current = { cols, rows };
      lettersRef.current = Array.from({ length: cols * rows }, () => ({
        char: rand(chars),
        color: rand(glitchColors),
        target: rand(glitchColors),
        progress: 1,
      }));
    };

    const hexToRgb = (hex) => {
      const m = hex.replace('#', '');
      return {
        r: parseInt(m.substring(0, 2), 16),
        g: parseInt(m.substring(2, 4), 16),
        b: parseInt(m.substring(4, 6), 16),
      };
    };
    const mix = (a, b, t) => {
      const ca = hexToRgb(a);
      const cb = hexToRgb(b);
      return `rgb(${Math.round(ca.r + (cb.r - ca.r) * t)}, ${Math.round(
        ca.g + (cb.g - ca.g) * t,
      )}, ${Math.round(ca.b + (cb.b - ca.b) * t)})`;
    };

    const draw = () => {
      const { cols } = gridRef.current;
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      ctx.font = `${fontSize}px 'Space Mono', monospace`;
      ctx.textBaseline = 'top';
      lettersRef.current.forEach((letter, i) => {
        const x = (i % cols) * charWidth;
        const y = Math.floor(i / cols) * charHeight;
        ctx.fillStyle = smooth ? mix(letter.color, letter.target, letter.progress) : letter.color;
        ctx.fillText(letter.char, x, y);
      });
    };

    const update = () => {
      const count = Math.max(1, Math.floor(lettersRef.current.length * 0.04));
      for (let i = 0; i < count; i += 1) {
        const idx = Math.floor(Math.random() * lettersRef.current.length);
        const letter = lettersRef.current[idx];
        if (!letter) continue;
        letter.char = rand(chars);
        letter.color = letter.target;
        letter.target = rand(glitchColors);
        letter.progress = 0;
      }
    };

    const loop = (now) => {
      if (smooth) {
        lettersRef.current.forEach((l) => {
          if (l.progress < 1) l.progress = Math.min(1, l.progress + 0.05);
        });
      }
      if (!reduce && now - lastRef.current > glitchSpeed) {
        update();
        lastRef.current = now;
      }
      draw();
      rafRef.current = requestAnimationFrame(loop);
    };

    build();
    draw();
    if (!reduce) rafRef.current = requestAnimationFrame(loop);
    const ro = new ResizeObserver(() => {
      build();
      draw();
    });
    ro.observe(parent);

    return () => {
      cancelAnimationFrame(rafRef.current);
      ro.disconnect();
    };
  }, [glitchColors, glitchSpeed, characters, fontSize, smooth]);

  return <canvas ref={canvasRef} className={`h-full w-full ${className}`} />;
}
