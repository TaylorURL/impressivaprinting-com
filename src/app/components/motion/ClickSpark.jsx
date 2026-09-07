import { useEffect } from 'react';

// A registration mark strikes the page where the pointer lands and fades out.
// It draws on its own fixed layer, so it answers the click without standing
// between the reader and anything they meant to hit.
export default function ClickSpark() {
  useEffect(() => {
    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)');
    const layer = document.createElement('div');
    layer.className = 'click-spark-layer';
    layer.setAttribute('aria-hidden', 'true');
    document.body.appendChild(layer);

    const onPointerDown = (event) => {
      if (reduced.matches) return;
      const spark = document.createElement('span');
      spark.className = 'click-spark';
      spark.style.left = `${event.clientX}px`;
      spark.style.top = `${event.clientY}px`;
      layer.appendChild(spark);
      spark.addEventListener('animationend', () => spark.remove(), { once: true });
    };

    window.addEventListener('pointerdown', onPointerDown, { passive: true });
    return () => {
      window.removeEventListener('pointerdown', onPointerDown);
      layer.remove();
    };
  }, []);

  return null;
}
