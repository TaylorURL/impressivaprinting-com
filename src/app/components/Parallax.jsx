// `distance` is total px of travel across the whole scroll window; negative
// values move the content up. The travel comes off a view timeline, so it
// runs on the compositor and stops on its own under reduced motion.
export default function Parallax({
  as = 'div',
  axis = 'y',
  distance = -80,
  className = '',
  style,
  children,
  ...rest
}) {
  const Tag = as;

  return (
    <Tag
      style={{ ...style, '--parallax-distance': `${distance}px` }}
      className={`parallax parallax-${axis} ${className}`}
      {...rest}
    >
      {children}
    </Tag>
  );
}
