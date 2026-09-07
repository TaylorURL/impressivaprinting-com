import { useEffect, useRef, useState } from 'react';
import { Link, NavLink, useNavigate } from 'react-router-dom';
import { ChevronDown, Menu, X } from 'lucide-react';
import { NAV_ITEMS, ROUTES } from '@constants/routes.js';
import { PRODUCTS } from '@constants/products.js';
import { useAuth } from '@hooks/useAuth.js';
import Picture from '@components/ui/Picture.jsx';
import SocialIcons from '@components/social/SocialIcons.jsx';

const PANEL_COLUMNS = [
  { head: 'Print', ids: ['business-cards', 'flyers', 'packaging'] },
  { head: 'Wide Format', ids: ['banners', 'signs'] },
  { head: 'Apply', ids: ['apparel', 'stickers'] },
];

function Brand() {
  return (
    <Link
      to={ROUTES.home}
      className="group flex h-11 items-center"
      aria-label="Impressiva Printing Home"
    >
      <Picture
        src="/logo"
        alt="Impressiva Printing"
        width="1200"
        height="410"
        widths={[560, 800, 1200]}
        sizes="(min-width: 640px) 176px, 160px"
        eager
        className="h-11 w-auto sm:h-12"
      />
    </Link>
  );
}

export default function Nav() {
  const { isAuthed, isAdmin, user, logout } = useAuth();
  const [pinned, setPinned] = useState(false);
  const [open, setOpen] = useState(false);
  const [megaOpen, setMegaOpen] = useState(false);
  const closeTimer = useRef(0);
  const navigate = useNavigate();

  useEffect(() => {
    const bar = document.querySelector('[data-nav-sentinel]');
    if (!bar) return;
    const observer = new IntersectionObserver(([entry]) => setPinned(!entry.isIntersecting), {
      rootMargin: '-8px 0px 0px 0px',
    });
    observer.observe(bar);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    if (!megaOpen) return;
    const onKey = (e) => {
      if (e.key === 'Escape') setMegaOpen(false);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [megaOpen]);

  // A grace period on the way out, so the pointer can cross the gap between
  // the trigger and the panel without the panel closing under it.
  const holdOpen = () => {
    window.clearTimeout(closeTimer.current);
    setMegaOpen(true);
  };
  const releaseOpen = () => {
    window.clearTimeout(closeTimer.current);
    closeTimer.current = window.setTimeout(() => setMegaOpen(false), 140);
  };

  useEffect(() => {
    document.body.style.overflow = open ? 'hidden' : '';
    return () => {
      document.body.style.overflow = '';
    };
  }, [open]);

  const handleLogout = () => {
    logout();
    setOpen(false);
    navigate(ROUTES.home);
  };

  return (
    <header className="fixed inset-x-0 top-0 z-nav">
      <div
        className={`relative transition-colors duration-300 ${pinned ? 'glass' : 'border-b border-transparent'}`}
      >
        <div className="mx-auto flex max-w-[1400px] items-center justify-between px-5 py-3 sm:px-8">
          <Brand />

          <nav className="hidden items-center gap-9 md:flex" aria-label="Primary">
            {NAV_ITEMS.map((item) =>
              item.to === ROUTES.products ? (
                <div
                  key={item.to}
                  className="relative"
                  onMouseEnter={holdOpen}
                  onMouseLeave={releaseOpen}
                  onFocus={holdOpen}
                  onBlur={releaseOpen}
                >
                  <button
                    type="button"
                    aria-expanded={megaOpen}
                    aria-haspopup="true"
                    aria-controls="nav-mega-panel"
                    onClick={() => setMegaOpen((v) => !v)}
                    className="spec flex h-11 items-center gap-1.5 text-xs uppercase tracking-[0.2em] text-paper-100/60 transition-colors hover:text-paper-100"
                  >
                    {item.label}
                    <ChevronDown
                      className={`h-3 w-3 transition-transform duration-300 ${megaOpen ? 'rotate-180' : ''}`}
                      aria-hidden
                    />
                  </button>
                </div>
              ) : (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.to === ROUTES.home}
                  className={({ isActive }) =>
                    `spec flex h-11 items-center text-xs uppercase tracking-[0.2em] transition-colors ${
                      isActive ? 'text-flare' : 'text-paper-100/60 hover:text-paper-100'
                    }`
                  }
                >
                  {item.label}
                </NavLink>
              ),
            )}
          </nav>

          <div className="hidden items-center gap-5 md:flex">
            <SocialIcons
              className="mr-2 h-11 items-center gap-4 border-r border-paper-100/12 pr-5"
              itemClassName="flex h-11 items-center text-paper-100/60 transition-transform hover:scale-110 hover:text-flare"
              iconClassName="h-[18px] w-[18px]"
            />
            {isAuthed ? (
              <>
                {isAdmin ? (
                  <Link
                    to={ROUTES.admin}
                    className="spec flex h-11 items-center text-xs uppercase tracking-[0.2em] text-paper-100/60 transition-colors hover:text-paper-100"
                  >
                    Admin
                  </Link>
                ) : null}
                <Link
                  to={ROUTES.portal}
                  className="spec link-wipe flex h-11 items-center text-xs uppercase tracking-[0.2em] text-paper-100"
                >
                  {user?.name?.split(' ')[0] || 'Portal'}
                </Link>
                <button
                  onClick={handleLogout}
                  className="spec pressable flex h-11 items-center text-xs uppercase tracking-[0.2em] text-paper-100/50 hover:text-flare"
                >
                  Out
                </button>
              </>
            ) : (
              <>
                <Link
                  to={ROUTES.login}
                  className="spec flex h-11 items-center text-xs uppercase tracking-[0.2em] text-paper-100/60 transition-colors hover:text-paper-100"
                >
                  Log In
                </Link>
                <Link
                  to={ROUTES.signup}
                  className="spec pressable flex h-11 items-center bg-flare px-5 text-xs font-700 uppercase tracking-[0.2em] text-white hover:bg-flare-deep"
                >
                  Start a Job
                </Link>
              </>
            )}
          </div>

          <button
            onClick={() => setOpen((v) => !v)}
            className="pressable flex h-11 items-center text-paper-100 md:hidden"
            aria-label="Toggle Menu"
            aria-expanded={open}
          >
            {open ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
          </button>
        </div>
        <div className="colorbar h-[3px]" aria-hidden>
          <span className="bg-flare" />
          <span className="bg-paper-300" />
          <span className="bg-ink-700" />
          <span className="bg-flare-deep" />
        </div>

        <div
          id="nav-mega-panel"
          className={`nav-mega-panel absolute inset-x-0 top-full border-b border-paper-100/10 bg-ink-950/95 backdrop-blur-xl ${
            megaOpen ? 'is-open' : ''
          }`}
          onMouseEnter={holdOpen}
          onMouseLeave={releaseOpen}
        >
          <div className="mx-auto grid max-w-[1400px] gap-8 px-5 py-10 sm:px-8 lg:grid-cols-[repeat(3,1fr)_1.1fr]">
            {PANEL_COLUMNS.map((column) => (
              <div key={column.head}>
                <p className="kicker text-paper-100/40">{column.head}</p>
                <ul className="mt-4 space-y-3">
                  {column.ids.map((id) => {
                    const product = PRODUCTS.find((item) => item.id === id);
                    if (!product) return null;
                    return (
                      <li key={id}>
                        <Link
                          to={ROUTES.products}
                          onClick={() => setMegaOpen(false)}
                          className="block border-l-2 border-transparent pl-3 transition-colors hover:border-flare"
                        >
                          <span className="font-head text-sm font-700 uppercase tracking-tight text-paper-100">
                            {product.name}
                          </span>
                          <span className="mt-1 block text-xs leading-relaxed text-paper-100/50">
                            {product.details.slice(0, 3).join(' · ')}
                          </span>
                        </Link>
                      </li>
                    );
                  })}
                </ul>
              </div>
            ))}

            <Link
              to={ROUTES.contact}
              onClick={() => setMegaOpen(false)}
              className="flex flex-col justify-between border border-paper-100/12 bg-ink-900 p-6 transition-colors hover:border-flare"
            >
              <div>
                <p className="kicker text-flare">Not On The List</p>
                <p className="display mt-3 text-3xl text-paper-100">Custom Quote</p>
              </div>
              <p className="mt-4 text-xs leading-relaxed text-paper-100/55">
                Send the spec and the studio will price it, whatever the format.
              </p>
            </Link>
          </div>
        </div>
      </div>

      {open ? (
        <div className="glass border-t border-paper-100/10 md:hidden">
          <nav className="mx-auto flex max-w-[1400px] flex-col px-5 py-2 sm:px-8">
            {NAV_ITEMS.map((item, i) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === ROUTES.home}
                onClick={() => setOpen(false)}
                className={({ isActive }) =>
                  `flex items-center gap-3 border-b border-paper-100/8 py-4 spec text-sm uppercase tracking-[0.2em] ${
                    isActive ? 'text-flare' : 'text-paper-100/70'
                  }`
                }
              >
                <span className="text-paper-100/25">{String(i + 1).padStart(2, '0')}</span>
                {item.label}
              </NavLink>
            ))}
            <div className="flex items-center justify-between border-b border-paper-100/8 py-4">
              <span className="spec text-xs uppercase tracking-[0.2em] text-paper-100/40">
                Follow
              </span>
              <SocialIcons
                className="gap-5"
                itemClassName="text-paper-100/70 hover:text-flare"
                iconClassName="h-5 w-5"
              />
            </div>
            <div className="flex gap-3 py-4">
              {isAuthed ? (
                <>
                  <Link
                    to={ROUTES.portal}
                    onClick={() => setOpen(false)}
                    className="spec flex-1 border border-paper-100/20 py-3 text-center text-xs uppercase tracking-[0.2em] text-paper-100"
                  >
                    Portal
                  </Link>
                  {isAdmin ? (
                    <Link
                      to={ROUTES.admin}
                      onClick={() => setOpen(false)}
                      className="spec flex-1 border border-paper-100/20 py-3 text-center text-xs uppercase tracking-[0.2em] text-paper-100"
                    >
                      Admin
                    </Link>
                  ) : null}
                  <button
                    onClick={handleLogout}
                    className="spec flex-1 bg-flare py-3 text-xs uppercase tracking-[0.2em] text-white"
                  >
                    Log Out
                  </button>
                </>
              ) : (
                <>
                  <Link
                    to={ROUTES.login}
                    onClick={() => setOpen(false)}
                    className="spec flex-1 border border-paper-100/20 py-3 text-center text-xs uppercase tracking-[0.2em] text-paper-100"
                  >
                    Log In
                  </Link>
                  <Link
                    to={ROUTES.signup}
                    onClick={() => setOpen(false)}
                    className="spec flex-1 bg-flare py-3 text-center text-xs uppercase tracking-[0.2em] text-white"
                  >
                    Start a Job
                  </Link>
                </>
              )}
            </div>
          </nav>
        </div>
      ) : null}
    </header>
  );
}
