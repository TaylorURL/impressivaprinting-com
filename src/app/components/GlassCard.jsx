export default function GlassCard({ as = 'div', className = '', sheen = true, children, ...rest }) {
  const Tag = as;
  return (
    <Tag className={`glass ${sheen ? 'glass-sheen' : ''} rounded-3xl ${className}`} {...rest}>
      {children}
    </Tag>
  );
}
