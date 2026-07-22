import { SITE } from '@constants/site.js';
import { SOCIAL_ICONS } from '@components/socialIconMap.jsx';

export default function SocialIcons({
  className = '',
  itemClassName = '',
  iconClassName = 'h-4 w-4',
}) {
  return (
    <div className={`flex items-center gap-3 ${className}`}>
      {SITE.socials.map((s) => {
        const Icon = SOCIAL_ICONS[s.icon];
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
