import { useRef, useEffect, useState } from 'react';
import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';

gsap.registerPlugin(ScrollTrigger);

// react-bits SplitText — splits text into chars/words and animates them in
// on scroll, with a GSAP stagger. Respects reduced-motion.
export default function SplitText({
  text = '',
  className = '',
  delay = 40,
  duration = 0.7,
  ease = 'power3.out',
  splitType = 'chars',
  from = { opacity: 0, y: 40 },
  to = { opacity: 1, y: 0 },
  threshold = 0.2,
  tag = 'span',
  onLetterAnimationComplete,
}) {
  const ref = useRef(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const el = ref.current;
    if (!el || !text) return;

    const reduce = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;

    const units = splitType === 'words' ? text.split(/(\s+)/) : Array.from(text);
    el.innerHTML = '';
    const nodes = units.map((unit) => {
      const span = document.createElement('span');
      span.style.display = 'inline-block';
      span.style.willChange = 'transform, opacity';
      span.textContent = unit === ' ' ? ' ' : unit;
      if (/^\s+$/.test(unit)) span.innerHTML = ' ';
      el.appendChild(span);
      return span;
    });
    setReady(true);

    if (reduce) {
      gsap.set(nodes, to);
      return undefined;
    }

    gsap.set(nodes, from);
    const tween = gsap.to(nodes, {
      ...to,
      duration,
      ease,
      stagger: delay / 1000,
      scrollTrigger: {
        trigger: el,
        start: `top bottom-=${Math.round(threshold * 100)}px`,
        toggleActions: 'play none none none',
        once: true,
      },
      onComplete: onLetterAnimationComplete,
    });

    return () => {
      tween.scrollTrigger?.kill();
      tween.kill();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [text, splitType]);

  const Tag = tag;
  return (
    <Tag
      ref={ref}
      className={className}
      style={{ display: 'inline-block', visibility: ready ? 'visible' : 'hidden' }}
    >
      {text}
    </Tag>
  );
}
