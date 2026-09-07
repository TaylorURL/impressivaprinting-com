import { SITE } from '@constants/site.js';
import { SOCIAL_ICONS } from '@components/social/socialIconMap.jsx';

// Hidden below wide screens — narrower viewports have no gutter and the rail
// would sit on top of content. mix-blend-difference is what keeps the marks
// legible as it floats over both dark and paper sections.
export default function SocialRail() {
  return (
    <aside
      aria-label="Follow Impressiva on Social Media"
      className="fixed left-5 top-1/2 z-sticky hidden -translate-y-1/2 mix-blend-difference min-[1500px]:block"
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
              className="pressable inline-grid h-9 w-9 place-items-center transition-transform duration-300 ease-editorial hover:scale-125"
            >
              <Icon className="h-[18px] w-[18px]" strokeWidth={1.5} />
            </a>
          );
        })}
        <span className="h-16 w-px bg-white/60" aria-hidden />
      </div>
    </aside>
  );
}
