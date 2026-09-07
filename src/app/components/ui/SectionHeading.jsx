export default function SectionHeading({ kicker, title, tone = 'ink', className = '', children }) {
  const ruleClass = tone === 'paper' ? 'border-ink-950/20' : 'border-paper-100/20';
  const dim = tone === 'paper' ? 'text-ink-950/55' : 'text-paper-100/55';
  const strong = tone === 'paper' ? 'text-ink-950' : 'text-paper-100';

  return (
    <div className={className}>
      <div className={`flex items-center justify-between border-b ${ruleClass} pb-3`}>
        <span className={`kicker ${dim}`}>{kicker}</span>
        {children ? <span className={`spec text-xs ${dim}`}>{children}</span> : null}
      </div>
      <h2 className={`display mt-5 text-5xl sm:text-6xl md:text-7xl ${strong}`}>{title}</h2>
    </div>
  );
}
