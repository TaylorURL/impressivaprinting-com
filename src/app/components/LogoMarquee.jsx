import { LOGOS } from '@constants/content.js';

// Trusted-by ticker. Two rows drifting opposite directions.
function Row({ reverse }) {
  const row = (
    <div className="flex shrink-0 items-center">
      {LOGOS.map((name, i) => (
        <span key={i} className="flex items-center">
          <span className="font-head text-xl font-800 uppercase tracking-tight text-paper-100/35 transition-colors hover:text-paper-100 sm:text-2xl">
            {name}
          </span>
          <span className="mx-8 h-1.5 w-1.5 rounded-full bg-flare/70" aria-hidden />
        </span>
      ))}
    </div>
  );
  return (
    <div className="flex overflow-hidden">
      <div className={`flex ${reverse ? 'animate-marquee-rev' : 'animate-marquee'}`}>
        {row}
        {row}
      </div>
    </div>
  );
}

export default function LogoMarquee() {
  return (
    <section className="border-y border-paper-100/10 bg-ink-900 py-10">
      <div className="mx-auto mb-8 max-w-[1400px] px-5 sm:px-8">
        <span className="kicker text-paper-100/45">Trusted by businesses across the city</span>
      </div>
      <div className="space-y-4">
        <Row />
        <Row reverse />
      </div>
    </section>
  );
}
