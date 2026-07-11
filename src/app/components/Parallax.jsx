import useScrollProgress from '@hooks/useScrollProgress.js';

// Translates its children on the Y axis as the element scrolls through view.
// `distance` = total px of travel across the full scroll window (negative moves up).
export default function Parallax({
  as = 'div',
  axis = 'y',
  distance = -80,
  className = '',
  children,
  ...rest
}) {
  const Tag = as;
  const [ref, progress] = useScrollProgress();
  const offset = (progress - 0.5) * distance;
  const transform =
    axis === 'x' ? `translate3d(${offset}px, 0, 0)` : `translate3d(0, ${offset}px, 0)`;

  return (
    <Tag ref={ref} style={{ transform }} className={`will-change-transform ${className}`} {...rest}>
      {children}
    </Tag>
  );
}
