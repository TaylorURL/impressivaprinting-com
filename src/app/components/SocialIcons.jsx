import { Facebook, Instagram } from 'lucide-react';
import { SITE } from '@constants/site.js';

function TikTokIcon({ className }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="currentColor" aria-hidden="true">
      <path d="M19.59 6.69a4.83 4.83 0 01-3.77-4.25V2h-3.45v13.67a2.89 2.89 0 01-5.2 1.74 2.89 2.89 0 012.89-4.7 2.86 2.86 0 01.88.16v-3.51a6.35 6.35 0 00-1-.08A6.34 6.34 0 108.36 21.9v-.02a6.31 6.31 0 006.31-6.31V8.87a8.16 8.16 0 004.77 1.52V6.94a4.84 4.84 0 01-.08-.25z" />
    </svg>
  );
}

const ICONS = {
  facebook: Facebook,
  instagram: Instagram,
  tiktok: TikTokIcon,
};

export default function SocialIcons({
  className = '',
  itemClassName = '',
  iconClassName = 'h-4 w-4',
}) {
  return (
    <div className={`flex items-center gap-3 ${className}`}>
      {SITE.socials.map((s) => {
        const Icon = ICONS[s.icon];
        return (
          <a
            key={s.label}
            href={s.href}
            target="_blank"
            rel="noreferrer"
            aria-label={s.label}
            className={`pressable inline-grid place-items-center transition-colors ${itemClassName}`}
          >
            <Icon className={iconClassName} strokeWidth={1.6} />
          </a>
        );
      })}
    </div>
  );
}
