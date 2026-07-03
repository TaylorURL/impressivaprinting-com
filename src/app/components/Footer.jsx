import { Link } from 'react-router-dom';
import { Mail, MapPin, Phone } from 'lucide-react';
import { NAV_ITEMS, ROUTES } from '@constants/routes.js';
import { SITE } from '@constants/site.js';

export default function Footer() {
  return (
    <footer className="relative mt-24 border-t border-white/10">
      <div className="mx-auto grid max-w-6xl gap-10 px-4 py-14 sm:px-6 md:grid-cols-[1.4fr_1fr_1fr]">
        <div>
          <Link to={ROUTES.home} className="flex items-center gap-2.5">
            <span className="grid h-9 w-9 place-items-center rounded-xl street-gradient text-ink-950">
              <span className="spray text-lg leading-none">IP</span>
            </span>
            <span className="spray text-xl text-white">
              Impressiva<span className="text-neon-magenta">.</span>
            </span>
          </Link>
          <p className="mt-4 max-w-sm text-sm leading-relaxed text-white/55">{SITE.blurb}</p>
          <div className="mt-5 flex gap-3">
            {SITE.socials.map((s) => (
              <a
                key={s.label}
                href={s.href}
                target="_blank"
                rel="noreferrer"
                className="pressable rounded-full border border-white/15 px-4 py-2 font-head text-xs font-600 uppercase tracking-wide text-white/60 hover:border-cyan/60 hover:text-white"
              >
                {s.label}
              </a>
            ))}
          </div>
        </div>

        <div>
          <h4 className="spray text-lg text-white">Explore</h4>
          <ul className="mt-4 space-y-2.5">
            {NAV_ITEMS.map((item) => (
              <li key={item.to}>
                <Link
                  to={item.to}
                  className="text-sm text-white/55 transition-colors hover:text-neon-cyan"
                >
                  {item.label}
                </Link>
              </li>
            ))}
            <li>
              <Link
                to={ROUTES.login}
                className="text-sm text-white/55 transition-colors hover:text-neon-cyan"
              >
                Account
              </Link>
            </li>
          </ul>
        </div>

        <div>
          <h4 className="spray text-lg text-white">The Shop</h4>
          <ul className="mt-4 space-y-3 text-sm text-white/55">
            <li className="flex items-center gap-2.5">
              <Phone className="h-4 w-4 text-neon-magenta" /> {SITE.phone}
            </li>
            <li className="flex items-center gap-2.5">
              <Mail className="h-4 w-4 text-neon-cyan" /> {SITE.email}
            </li>
            <li className="flex items-start gap-2.5">
              <MapPin className="mt-0.5 h-4 w-4 text-neon-acid" /> {SITE.address}
            </li>
            <li className="pl-6 text-white/40">{SITE.hours}</li>
          </ul>
        </div>
      </div>

      <div className="border-t border-white/10">
        <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-2 px-4 py-6 text-xs text-white/40 sm:flex-row sm:px-6">
          <span>
            © {2026} {SITE.name}. All rights reserved.
          </span>
          <span className="font-graff text-base text-white/50">Print Loud. Print Proud.</span>
        </div>
      </div>
    </footer>
  );
}
