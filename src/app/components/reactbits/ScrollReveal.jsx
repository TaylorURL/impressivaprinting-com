import { useEffect, useMemo, useRef } from 'react';
import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';

gsap.registerPlugin(ScrollTrigger);

// react-bits ScrollReveal — a paragraph whose words rise from a blurred,
// dimmed state to full opacity as the block is scrubbed through the viewport.
export default function ScrollReveal({
  children,
  className = '',
  baseOpacity = 0.12,
  baseRotation = 3,
  blurStrength = 4,
  containerClassName = '',
}) {
  const ref = useRef(null);
  const words = useMemo(() => String(children).split(/(\s+)/), [children]);

  useEffect(() => {
    const el = ref.current;
    if (!el) return undefined;
    const reduce = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
    const targets = el.querySelectorAll('.rb-reveal-word');
    if (reduce) {
      gsap.set(targets, { opacity: 1, filter: 'blur(0px)', y: 0 });
      return undefined;
    }

    const ctx = gsap.context(() => {
      gsap.fromTo(
        targets,
        { opacity: baseOpacity, filter: `blur(${blurStrength}px)`, y: 8 },
        {
          opacity: 1,
          filter: 'blur(0px)',
          y: 0,
          ease: 'none',
          stagger: 0.05,
          scrollTrigger: {
            trigger: el,
            start: 'top bottom-=15%',
            end: 'bottom center',
            scrub: true,
          },
        },
      );
    }, el);

    return () => ctx.revert();
  }, [children, baseOpacity, baseRotation, blurStrength]);

  return (
    <p ref={ref} className={`${containerClassName} ${className}`}>
      {words.map((word, i) =>
        /^\s+$/.test(word) ? (
          <span key={i}> </span>
        ) : (
          <span key={i} className="rb-reveal-word inline-block will-change-[transform,filter,opacity]">
            {word}
          </span>
        ),
      )}
    </p>
  );
}
