import { useRef, useMemo } from 'react';
import { motion, useInView } from 'framer-motion';

// react-bits BlurText — reveals text word-by-word (or char-by-char) with a
// blur-to-sharp transition when it scrolls into view.
export default function BlurText({
  text = '',
  delay = 120,
  className = '',
  animateBy = 'words',
  direction = 'top',
  threshold = 0.2,
  rootMargin = '-40px',
  as = 'p',
}) {
  const ref = useRef(null);
  const inView = useInView(ref, { once: true, amount: threshold, margin: rootMargin });
  const segments = useMemo(
    () => (animateBy === 'words' ? text.split(' ') : Array.from(text)),
    [text, animateBy],
  );

  const offset = direction === 'top' ? -14 : 14;
  const hidden = { filter: 'blur(10px)', opacity: 0, y: offset };
  const shown = { filter: 'blur(0px)', opacity: 1, y: 0 };

  const MotionTag = motion[as] || motion.p;

  return (
    <MotionTag ref={ref} className={className} style={{ display: 'inline-block' }}>
      {segments.map((seg, i) => (
        <motion.span
          key={i}
          initial={hidden}
          animate={inView ? shown : hidden}
          transition={{
            duration: 0.55,
            ease: [0.16, 1, 0.3, 1],
            delay: (i * delay) / 1000,
          }}
          style={{ display: 'inline-block', willChange: 'transform, filter, opacity' }}
        >
          {seg === '' ? ' ' : seg}
          {animateBy === 'words' && i < segments.length - 1 ? ' ' : ''}
        </motion.span>
      ))}
    </MotionTag>
  );
}
