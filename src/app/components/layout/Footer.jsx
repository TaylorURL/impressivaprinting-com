import { Link } from 'react-router-dom';
import { ROUTES } from '@constants/routes.js';
import { SITE } from '@constants/site.js';
import { ColorBar } from '@components/ui/PrintMarks.jsx';
import Parallax from '@components/motion/Parallax.jsx';
import Picture from '@components/ui/Picture.jsx';
import { SOCIAL_ICONS } from '@components/social/socialIconMap.jsx';
import { currentYear } from '@utils/format.js';

export default function Footer({ children }) {
  return (
    <footer className="relative mt-32 bg-ink-950">
      <ColorBar className="h-2" />

      <div className="overflow-hidden border-b border-paper-100/10 py-10">
        <Parallax
          axis="x"
          distance={140}
          className="display whitespace-nowrap px-5 text-[18vw] leading-[0.8] text-paper-100/[0.07] sm:px-8"
        >
          IMPRESSIVA PRINTING · IMPRESSIVA PRINTING
        </Parallax>
      </div>

      <div className="mx-auto max-w-[1400px] px-5 py-12 sm:px-8">
        <div className="flex flex-col gap-8 border-b border-paper-100/10 pb-10 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <Picture
              src="/logo"
              alt="Impressiva Printing"
              width="1200"
              height="410"
              widths={[560, 1200]}
              sizes="200px"
              className="h-14 w-auto"
            />
            <p className="mt-5 max-w-md text-sm leading-relaxed text-paper-100/55">{SITE.blurb}</p>
          </div>

          <div className="flex items-center gap-4">
            {SITE.socials.map((s) => {
              const Icon = SOCIAL_ICONS[s.icon];
              return (
                <a
                  key={s.label}
                  href={s.href}
                  target="_blank"
                  rel="noreferrer"
                  aria-label={s.label}
                  className="grid h-10 w-10 place-items-center border border-paper-100/15 text-paper-100/70 transition-colors duration-300 hover:border-flare hover:text-flare"
                >
                  <Icon className="h-4 w-4" strokeWidth={1.8} />
                </a>
              );
            })}
          </div>
        </div>

        {/* Name, address and phone in that order, spelled exactly as the
            LocalBusiness markup in index.html spells them. */}
        <address className="spec mt-8 flex flex-col gap-x-6 gap-y-2 text-xs not-italic text-paper-100/60 sm:flex-row sm:flex-wrap sm:items-center">
          <span className="text-paper-100/85">{SITE.name}</span>
          <span>{SITE.address}</span>
          <a href={`tel:${SITE.phone.replace(/\D/g, '')}`} className="hover:text-flare">
            {SITE.phone}
          </a>
          <a href={`mailto:${SITE.email}`} className="break-all hover:text-flare">
            {SITE.email}
          </a>
          <span className="text-paper-100/40">{SITE.hours}</span>
        </address>
      </div>

      <div className="border-t border-paper-100/10">
        <div className="mx-auto flex max-w-[1400px] flex-col items-start justify-between gap-2 px-5 py-6 sm:flex-row sm:items-center sm:px-8">
          <span className="spec text-[11px] uppercase tracking-[0.2em] text-paper-100/40">
            © {currentYear()} {SITE.name}. All Rights Reserved
          </span>
          <div className="spec flex flex-wrap items-center gap-x-4 gap-y-2 text-[11px] uppercase tracking-[0.2em] text-paper-100/40">
            <Link to={ROUTES.privacy} className="hover:text-flare">
              Privacy
            </Link>
            <Link to={ROUTES.terms} className="hover:text-flare">
              Terms
            </Link>
            <Link to={ROUTES.contact} className="hover:text-flare">
              Contact
            </Link>
          </div>
        </div>
      </div>

      {/* The closing slot sits inside the footer, so what is mounted here
          takes this band's ground and the paper ink the rest of the block is
          written in. */}
      <div className="text-paper-100">{children}</div>
    </footer>
  );
}
