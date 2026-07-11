import { useEffect, useRef, useState } from 'react';

const CHARS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!<>-_\\/[]{}=+*#';

// react-bits DecryptedText — scrambles characters then resolves them to the
// real text. Runs once when it enters view (great for spec/mono readouts).
export default function DecryptedText({
  text = '',
  speed = 45,
  className = '',
  encryptedClassName = '',
  as = 'span',
}) {
  const ref = useRef(null);
  const [output, setOutput] = useState(text);
  const [revealed, setRevealed] = useState(0);
  const [started, setStarted] = useState(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return undefined;
    const reduce = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
    if (reduce) {
      setRevealed(text.length);
      setOutput(text);
      return undefined;
    }
    const io = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setStarted(true);
          io.disconnect();
        }
      },
      { threshold: 0.4 },
    );
    io.observe(el);
    return () => io.disconnect();
  }, [text]);

  useEffect(() => {
    if (!started) return undefined;
    let frame = 0;
    const id = setInterval(() => {
      frame += 1;
      const done = Math.floor(frame / 2);
      setRevealed(done);
      setOutput(
        Array.from(text)
          .map((ch, i) => {
            if (ch === ' ') return ' ';
            if (i < done) return ch;
            return CHARS[Math.floor(Math.random() * CHARS.length)];
          })
          .join(''),
      );
      if (done >= text.length) clearInterval(id);
    }, speed);
    return () => clearInterval(id);
  }, [started, text, speed]);

  const Tag = as;
  return (
    <Tag ref={ref} className={className} aria-label={text}>
      {Array.from(output).map((ch, i) => (
        <span key={i} className={i < revealed ? '' : encryptedClassName} aria-hidden>
          {ch}
        </span>
      ))}
    </Tag>
  );
}
