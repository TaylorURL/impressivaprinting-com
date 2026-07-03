import { useEffect, useState } from 'react';

// Thin reading-progress bar fixed under the nav — page scroll made visible.
export default function ScrollProgressBar() {
  const [p, setP] = useState(0);

  useEffect(() => {
    let raf = 0;
    const compute = () => {
      raf = 0;
      const max = document.documentElement.scrollHeight - window.innerHeight;
      setP(max <= 0 ? 0 : Math.min(1, window.scrollY / max));
    };
    const onScroll = () => {
      if (!raf) raf = requestAnimationFrame(compute);
    };
    compute();
    window.addEventListener('scroll', onScroll, { passive: true });
    window.addEventListener('resize', onScroll, { passive: true });
    return () => {
      window.removeEventListener('scroll', onScroll);
      window.removeEventListener('resize', onScroll);
      if (raf) cancelAnimationFrame(raf);
    };
  }, []);

  return (
    <div className="fixed inset-x-0 top-0 z-[60] h-[2px] bg-transparent">
      <div
        className="h-full bg-flare transition-[width] duration-150 ease-out"
        style={{ width: `${p * 100}%` }}
      />
    </div>
  );
}
