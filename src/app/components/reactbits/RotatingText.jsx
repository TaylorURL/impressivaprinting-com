import { useEffect, useState, useCallback } from 'react';
import { AnimatePresence, motion } from 'framer-motion';

// react-bits RotatingText — cycles through a list of words, animating each in
// and out per-character. Used for the hero's rotating product line.
export default function RotatingText({
  texts = [],
  rotationInterval = 2200,
  className = '',
  mainClassName = '',
  staggerDuration = 0.02,
  splitBy = 'characters',
}) {
  const [index, setIndex] = useState(0);

  const elements = useCallback(
    (text) => (splitBy === 'characters' ? Array.from(text) : text.split(splitBy)),
    [splitBy],
  );

  useEffect(() => {
    if (texts.length <= 1) return undefined;
    const reduce = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
    if (reduce) return undefined;
    const id = setInterval(() => setIndex((i) => (i + 1) % texts.length), rotationInterval);
    return () => clearInterval(id);
  }, [texts, rotationInterval]);

  const current = texts[index] ?? '';

  return (
    <span className={`inline-flex overflow-hidden ${mainClassName}`}>
      <AnimatePresence mode="wait" initial={false}>
        <motion.span key={index} className={`inline-flex ${className}`} aria-label={current}>
          {elements(current).map((ch, i) => (
            <motion.span
              key={i}
              className="inline-block"
              initial={{ y: '100%', opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              exit={{ y: '-110%', opacity: 0 }}
              transition={{
                duration: 0.4,
                ease: [0.16, 1, 0.3, 1],
                delay: i * staggerDuration,
              }}
            >
              {ch === ' ' ? ' ' : ch}
            </motion.span>
          ))}
        </motion.span>
      </AnimatePresence>
    </span>
  );
}
