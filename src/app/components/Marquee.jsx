// Editorial ticker. Duplicated content loops seamlessly via the -50% keyframe.
export default function Marquee({ items, reverse = false, separator = '/', className = '' }) {
  const row = (
    <div className="flex shrink-0 items-center">
      {items.map((item, i) => (
        <span key={i} className="flex items-center">
          <span className="display whitespace-nowrap px-6 text-3xl sm:text-4xl">{item}</span>
          <span className="text-flare" aria-hidden>
            {separator}
          </span>
        </span>
      ))}
    </div>
  );

  return (
    <div className={`flex overflow-hidden ${className}`}>
      <div className={`flex ${reverse ? 'animate-marquee-rev' : 'animate-marquee'}`}>
        {row}
        {row}
      </div>
    </div>
  );
}
