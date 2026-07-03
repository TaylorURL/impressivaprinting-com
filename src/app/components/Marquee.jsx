// Infinite street-ticker. Content is duplicated so the -50% translate loops seamlessly.
export default function Marquee({ items, className = '' }) {
  const row = (
    <div className="flex shrink-0 items-center gap-6 pr-6">
      {items.map((item, i) => (
        <span key={i} className="flex items-center gap-6">
          <span className="spray text-2xl text-white/90">{item}</span>
          <span className="text-neon-magenta">✦</span>
        </span>
      ))}
    </div>
  );

  return (
    <div className={`relative flex overflow-hidden ${className}`}>
      <div className="flex animate-marquee">
        {row}
        {row}
      </div>
    </div>
  );
}
