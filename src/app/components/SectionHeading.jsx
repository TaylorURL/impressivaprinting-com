import { SplitText } from '@reactbits';

// Editorial section header: index number + mono kicker on a hairline rule,
// then a heavy Archivo title. Tone-aware for the dark/paper rhythm.
// The title characters stagger in on scroll via react-bits SplitText.
export default function SectionHeading({
  index,
  kicker,
  title,
  tone = 'ink',
  className = '',
  children,
}) {
  const ruleClass = tone === 'paper' ? 'border-ink-950/20' : 'border-paper-100/20';
  const dim = tone === 'paper' ? 'text-ink-950/55' : 'text-paper-100/55';
  const strong = tone === 'paper' ? 'text-ink-950' : 'text-paper-100';

  return (
    <div className={className}>
      <div className={`flex items-center justify-between border-b ${ruleClass} pb-3`}>
        <span className={`kicker ${dim}`}>
          {index ? <span className="text-flare">{index}</span> : null}
          {index ? ' / ' : ''}
          {kicker}
        </span>
        {children ? <span className={`spec text-xs ${dim}`}>{children}</span> : null}
      </div>
      <h2 className={`display mt-5 text-5xl sm:text-6xl md:text-7xl ${strong}`}>
        {typeof title === 'string' ? (
          <SplitText text={title} splitType="chars" delay={26} duration={0.6} />
        ) : (
          title
        )}
      </h2>
    </div>
  );
}
