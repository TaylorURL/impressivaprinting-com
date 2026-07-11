import { Link, useLocation } from 'react-router-dom';
import { NAV_ITEMS, ROUTES } from '@constants/routes.js';
import { SITE } from '@constants/site.js';
import { pad2 } from '@utils/format.js';
import { ColorBar } from '@components/PrintMarks.jsx';
import Parallax from '@components/Parallax.jsx';
import SocialIcons from '@components/SocialIcons.jsx';
import { ShinyText } from '@reactbits';

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
            IMPRESSIVA · PRINT LOUD · IMPRESSIVA
          </Parallax>
        </div>
      ) : null}

      <div className="mx-auto grid max-w-[1400px] gap-10 px-5 py-14 sm:px-8 md:grid-cols-[1.6fr_1fr_1fr]">
        <div>
          <img
            src="/logo.svg"
            alt="Impressiva Printing"
            className="h-14 w-auto"
            width="600"
            height="260"
          />
          <p className="mt-6 max-w-sm text-sm leading-relaxed text-paper-100/55">{SITE.blurb}</p>
          <div className="mt-6 flex items-center gap-5">
            <span className="spec text-xs uppercase tracking-[0.2em] text-paper-100/40">
              Follow
            </span>
            <SocialIcons
              className="gap-4"
              itemClassName="text-paper-100/60 hover:text-flare"
              iconClassName="h-5 w-5"
            />
          </div>
        </div>

        <div>
          <span className="kicker text-paper-100/40">Index</span>
          <ul className="mt-5 space-y-3">
            {NAV_ITEMS.map((item, i) => (
              <li key={item.to} className="flex items-center gap-3">
                <span className="spec text-xs text-paper-100/25">{pad2(i + 1)}</span>
                <Link
                  to={item.to}
                  className="spec text-xs uppercase tracking-[0.15em] text-paper-100/70 hover:text-flare"
                >
                  {item.label}
                </Link>
              </li>
            ))}
            <li className="flex items-center gap-3">
              <span className="spec text-xs text-paper-100/25">{pad2(NAV_ITEMS.length + 1)}</span>
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
          <ShinyText
            text="Print Loud / Print Proud"
            className="spec text-[11px] uppercase tracking-[0.2em]"
            speed={6}
          />
        </div>
      </div>
    </footer>
  );
}
