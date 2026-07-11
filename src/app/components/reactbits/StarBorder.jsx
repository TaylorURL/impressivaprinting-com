// react-bits StarBorder — a pill/box whose border has two glints of light
// orbiting its edges. Wraps a button or link. Styling lives in .rb-star* CSS.
export default function StarBorder({
  as = 'button',
  className = '',
  color = '#e5352b',
  speed = '5s',
  thickness = 1,
  children,
  ...rest
}) {
  const Tag = as;
  return (
    <Tag
      className={`rb-star ${className}`}
      style={{ padding: `${thickness}px 0`, '--rb-star-color': color, '--rb-star-speed': speed }}
      {...rest}
    >
      <span className="rb-star__glow rb-star__glow--bottom" style={{ background: `radial-gradient(circle, ${color}, transparent 12%)` }} />
      <span className="rb-star__glow rb-star__glow--top" style={{ background: `radial-gradient(circle, ${color}, transparent 12%)` }} />
      <span className="rb-star__content">{children}</span>
    </Tag>
  );
}
