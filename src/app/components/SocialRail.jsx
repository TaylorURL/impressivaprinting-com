import { SITE } from '@constants/site.js';
import { SOCIAL_ICONS } from '@components/socialIconMap.jsx';

// Persistent vertical social rail pinned to the left gutter. Shown only on
// wide screens where the centered layout leaves margin, so it never overlaps
// content. mix-blend-difference keeps the white marks legible over both the
// dark and the light (paper) sections it floats across.
export default function SocialRail() {
  return (
    <aside
      aria-label="Follow Impressiva on social media"
      className="fixed left-5 top-1/2 z-40 hidden -translate-y-1/2 mix-blend-difference min-[1500px]:block"
    >
      <div className="flex flex-col items-center gap-4 text-white">
        <span className="h-16 w-px bg-white/60" aria-hidden />
        {SITE.socials.map((s) => {
          const Icon = SOCIAL_ICONS[s.icon];
          return (
            <a
              key={s.label}
              href={s.href}
              target="_blank"
              rel="noreferrer"
              aria-label={s.label}
              className="pressable inline-grid h-9 w-9 place-items-center transition-transform duration-200 ease-editorial hover:scale-125"
            >
              <Icon className="h-[18px] w-[18px]" strokeWidth={1.7} />
            </a>
          );
        })}
        <span className="spec rotate-180 text-[10px] uppercase tracking-[0.32em] text-white/80 [writing-mode:vertical-rl]">
          Follow
        </span>
        <span className="h-16 w-px bg-white/60" aria-hidden />
      </div>
    </aside>
  );
}
