import { ArrowUpRight } from 'lucide-react';
import { SITE } from '@constants/site.js';
import { PORTFOLIO } from '@constants/content.js';
import { SOCIAL_ICONS } from '@components/socialIconMap.jsx';
import Reveal from '@components/Reveal.jsx';
import SectionHeading from '@components/SectionHeading.jsx';

const WRAP = 'mx-auto max-w-[1400px] px-5 sm:px-8';
const INSTAGRAM = SITE.socials.find((s) => s.icon === 'instagram');

function PlatformCard({ platform }) {
  const Icon = SOCIAL_ICONS[platform.icon];
  return (
    <a
      href={platform.href}
      target="_blank"
      rel="noreferrer"
      className="pressable group relative flex flex-col overflow-hidden border border-ink-950/12 bg-white p-6 transition-[transform,border-color] duration-300 ease-editorial hover:-translate-y-1 hover:border-ink-950/25"
    >
      <span
        className="absolute inset-x-0 top-0 h-1 origin-left scale-x-0 transition-transform duration-300 ease-editorial group-hover:scale-x-100"
        style={{ backgroundColor: platform.accent }}
        aria-hidden
      />
      <div className="flex items-start justify-between">
        <span className="relative grid h-12 w-12 place-items-center overflow-hidden border border-ink-950/12">
          <span
            className="absolute inset-0 opacity-0 transition-opacity duration-300 group-hover:opacity-100"
            style={{ backgroundColor: platform.accent }}
            aria-hidden
          />
          <Icon
            className="relative h-6 w-6 text-ink-950 transition-colors duration-300 group-hover:text-white"
            strokeWidth={1.7}
          />
        </span>
        <ArrowUpRight
          className="h-5 w-5 text-ink-950/40 transition-all duration-300 ease-editorial group-hover:-translate-y-0.5 group-hover:translate-x-0.5 group-hover:text-flare"
          strokeWidth={2}
        />
      </div>
      <h3 className="mt-6 font-head text-xl font-800 uppercase tracking-tight text-ink-950">
        {platform.label}
      </h3>
      <p className="spec mt-1 text-xs text-ink-950/50">{platform.handle}</p>
      <p className="mt-3 text-sm leading-relaxed text-ink-950/60">{platform.blurb}</p>
      <span className="spec link-wipe mt-6 inline-flex w-fit items-center gap-1 text-xs uppercase tracking-[0.2em] text-ink-950">
        Follow
      </span>
    </a>
  );
}

function StripImage({ item }) {
  return (
    <a
      href={INSTAGRAM.href}
      target="_blank"
      rel="noreferrer"
      className="group relative block aspect-square w-52 shrink-0 overflow-hidden border border-ink-950/12 sm:w-60"
      aria-label={`${item.title} — view on Instagram`}
    >
      <img
        src={item.image}
        alt={item.title}
        loading="lazy"
        className="h-full w-full object-cover transition-transform duration-500 ease-editorial group-hover:scale-105"
      />
      <div className="absolute inset-0 bg-ink-950/0 transition-colors duration-300 group-hover:bg-ink-950/40" />
      <span className="absolute inset-0 grid place-items-center opacity-0 transition-opacity duration-300 group-hover:opacity-100">
        <SOCIAL_ICONS.instagram className="h-7 w-7 text-white" strokeWidth={1.7} />
      </span>
    </a>
  );
}

const StripRow = () => (
  <div className="flex shrink-0 items-center gap-4 pr-4">
    {PORTFOLIO.map((item) => (
      <StripImage key={item.id} item={item} />
    ))}
  </div>
);

export default function SocialSection() {
  return (
    <section className="grain relative overflow-hidden bg-paper-50 text-ink-950">
      <div className={`relative ${WRAP} py-20 sm:py-24`}>
        <Reveal>
          <SectionHeading index="05" kicker="Follow Along" title="On Social" tone="paper">
            <a
              href={INSTAGRAM.href}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1 hover:text-flare"
            >
              {SITE.handle} <ArrowUpRight className="h-3.5 w-3.5" />
            </a>
          </SectionHeading>
        </Reveal>

        <div className="mt-12 grid gap-5 sm:grid-cols-3">
          {SITE.socials.map((platform, i) => (
            <Reveal key={platform.label} delay={i * 70}>
              <PlatformCard platform={platform} />
            </Reveal>
          ))}
        </div>
      </div>

      {/* Full-bleed moving strip of recent shop work */}
      <div className="relative pb-20 sm:pb-24">
        <div className={`${WRAP} flex items-end justify-between border-t border-ink-950/12 pb-8 pt-8`}>
          <div>
            <span className="kicker text-flare">On the grid</span>
            <h3 className="display mt-2 text-3xl text-ink-950 sm:text-4xl">Straight from the shop</h3>
          </div>
          <a
            href={INSTAGRAM.href}
            target="_blank"
            rel="noreferrer"
            className="spec link-wipe hidden items-center gap-1.5 text-xs uppercase tracking-[0.2em] text-ink-950 hover:text-flare sm:inline-flex"
          >
            Follow {SITE.handle} <ArrowUpRight className="h-4 w-4" />
          </a>
        </div>

        <div className="flex overflow-hidden [mask-image:linear-gradient(90deg,transparent,black_6%,black_94%,transparent)]">
          <div className="flex animate-marquee hover:[animation-play-state:paused]">
            <StripRow />
            <StripRow />
          </div>
        </div>
      </div>
    </section>
  );
}
