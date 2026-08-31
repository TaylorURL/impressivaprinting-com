// `tone` picks which side of the dark/light section rhythm this panel sits on.
export default function Panel({
  as = 'div',
  tone = 'ink',
  marks = false,
  className = '',
  children,
  ...rest
}) {
  const Tag = as;
  const toneClass =
    tone === 'paper'
      ? 'bg-paper-100 text-ink-950 border-ink-950/15'
      : 'bg-ink-900 text-paper-100 border-paper-100/12';
  return (
    <Tag
      className={`relative border ${toneClass} ${marks ? 'cropmarks' : ''} ${className}`}
      {...rest}
    >
      {children}
    </Tag>
  );
}
