export default function SectionHeading({ kicker, title, accent, align = 'left', className = '' }) {
  const alignment = align === 'center' ? 'items-center text-center' : 'items-start text-left';
  return (
    <div className={`flex flex-col ${alignment} gap-3 ${className}`}>
      {kicker ? (
        <span className="font-graff text-lg text-neon-cyan rotate-[-2deg]">{kicker}</span>
      ) : null}
      <h2 className="spray text-4xl leading-[0.95] text-white sm:text-5xl md:text-6xl">
        {title} {accent ? <span className="clip-text street-gradient">{accent}</span> : null}
      </h2>
    </div>
  );
}
