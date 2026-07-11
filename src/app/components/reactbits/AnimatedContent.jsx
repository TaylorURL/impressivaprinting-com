import { useEffect, useRef, useState } from 'react';
import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';

gsap.registerPlugin(ScrollTrigger);

// react-bits AnimatedContent — a scroll-triggered wrapper that slides/scales
// its children in from a chosen direction. A richer sibling of <Reveal/>.
export default function AnimatedContent({
  children,
  distance = 80,
  direction = 'vertical',
  reverse = false,
  duration = 0.8,
  ease = 'power3.out',
  delay = 0,
  threshold = 0.1,
  scale = 1,
  className = '',
}) {
  const ref = useRef(null);
  const [mounted, setMounted] = useState(false);

  useEffect(() => setMounted(true), []);

  useEffect(() => {
    const el = ref.current;
    if (!el) return undefined;
    const reduce = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
    if (reduce) {
      gsap.set(el, { opacity: 1, x: 0, y: 0, scale: 1 });
      return undefined;
    }

    const axis = direction === 'horizontal' ? 'x' : 'y';
    const offset = reverse ? -distance : distance;

    gsap.set(el, { [axis]: offset, scale, opacity: 0 });
    const tween = gsap.to(el, {
      [axis]: 0,
      scale: 1,
      opacity: 1,
      duration,
      ease,
      delay,
      scrollTrigger: {
        trigger: el,
        start: `top bottom-=${threshold * 100}px`,
        toggleActions: 'play none none none',
        once: true,
      },
    });

    return () => {
      tween.scrollTrigger?.kill();
      tween.kill();
    };
  }, [mounted, distance, direction, reverse, duration, ease, delay, threshold, scale]);

  return (
    <div ref={ref} className={className} style={{ opacity: mounted ? undefined : 0 }}>
      {children}
    </div>
  );
}
