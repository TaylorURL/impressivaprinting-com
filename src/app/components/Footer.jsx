import { Link, useLocation } from 'react-router-dom';
import { NAV_ITEMS, ROUTES } from '@constants/routes.js';
import { SITE } from '@constants/site.js';
import { ColorBar } from '@components/PrintMarks.jsx';
import Parallax from '@components/Parallax.jsx';
import { SOCIAL_ICONS } from '@components/socialIconMap.jsx';

export default function Footer() {
  const isHome = useLocation().pathname === ROUTES.home;

  return (
    <footer className="relative mt-32 bg-ink-950">
      <ColorBar className="h-2" />

      {/* Oversized wordmark band — home only, drifts sideways on scroll */}
      {isHome ? (
        <div className="overflow-hidden border-b border-paper-100/10 py-10">
          <Parallax
            axis="x"
            distance={140}
            className="display whitespace-nowrap px-5 text-[18vw] leading-[0.8] text-paper-100/[0.07] sm:px-8"
          >
            IMPRESSIVA PRINTING · IMPRESSIVA PRINTING
          </Parallax>
        </div>
      ) : null}

      <div className="mx-auto grid max-w-[1400px] gap-10 px-5 py-14 sm:px-8 md:grid-cols-[1.6fr_1fr_1fr]">
        <div>
          <img
            src="/logo.png"
            alt="Impressiva Printing"
            className="h-14 w-auto"
            width="1200"
            height="410"
          />
          <p className="mt-6 max-w-sm text-sm leading-relaxed text-paper-100/55">{SITE.blurb}</p>
          <div className="mt-8">
            <span className="kicker text-paper-100/40">Follow {SITE.handle}</span>
            <div className="mt-4 flex flex-col gap-2.5">
              {SITE.socials.map((s) => {
                const Icon = SOCIAL_ICONS[s.icon];
                return (
                  <a
                    key={s.label}
                    href={s.href}
                    target="_blank"
                    rel="noreferrer"
                    className="group flex items-center gap-3 text-paper-100/70 transition-colors hover:text-paper-100"
                  >
                    <span className="grid h-9 w-9 place-items-center border border-paper-100/15 transition-colors duration-300 group-hover:border-flare group-hover:text-flare">
                      <Icon className="h-4 w-4" strokeWidth={1.7} />
                    </span>
                    <span className="spec text-xs uppercase tracking-[0.15em]">{s.label}</span>
                    <span className="spec ml-auto text-[11px] text-paper-100/40">{s.handle}</span>
                  </a>
                );
              })}
            </div>
          </div>
        </div>

        <div>
          <span className="kicker text-paper-100/40">Index</span>
          <ul className="mt-5 space-y-3">
            {NAV_ITEMS.map((item, i) => (
              <li key={item.to} className="flex items-center gap-3">
                <span className="spec text-xs text-paper-100/25">
                  {String(i + 1).padStart(2, '0')}
                </span>
                <Link
                  to={item.to}
                  className="spec text-xs uppercase tracking-[0.15em] text-paper-100/70 hover:text-flare"
                >
                  {item.label}
                </Link>
              </li>
            ))}
            <li className="flex items-center gap-3">
              <span className="spec text-xs text-paper-100/25">
                {String(NAV_ITEMS.length + 1).padStart(2, '0')}
              </span>
              <Link
                to={ROUTES.login}
                className="spec text-xs uppercase tracking-[0.15em] text-paper-100/70 hover:text-flare"
              >
                Account
              </Link>
            </li>
          </ul>
        </div>

        <div>
          <span className="kicker text-paper-100/40">Contact</span>
          <ul className="mt-5 space-y-3 text-sm text-paper-100/70">
            <li className="spec text-xs">{SITE.phone}</li>
            <li className="spec break-all text-xs">{SITE.email}</li>
            <li className="spec text-xs leading-relaxed">{SITE.address}</li>
            <li className="spec text-xs text-paper-100/40">{SITE.hours}</li>
          </ul>
        </div>
      </div>

      <div className="border-t border-paper-100/10">
        <div className="mx-auto flex max-w-[1400px] flex-col items-start justify-between gap-2 px-5 py-6 sm:flex-row sm:items-center sm:px-8">
          <span className="spec text-[11px] uppercase tracking-[0.2em] text-paper-100/40">
            © 2026 {SITE.name} — All Rights Reserved
          </span>
          <span className="spec text-[11px] uppercase tracking-[0.2em] text-paper-100/40">
            Custom Print Studio <span className="text-flare">/</span> {SITE.address.split(',').pop().trim()}
          </span>
        </div>
      </div>
    </footer>
  );
}
