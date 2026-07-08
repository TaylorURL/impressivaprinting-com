import { useEffect, useState } from 'react';
import { Link, NavLink, useNavigate } from 'react-router-dom';
import { Menu, X } from 'lucide-react';
import { NAV_ITEMS, ROUTES } from '@constants/routes.js';
import { useAuth } from '@hooks/useAuth.js';

function Brand() {
  return (
    <Link to={ROUTES.home} className="group flex items-baseline gap-2">
      <span className="display text-2xl leading-none text-paper-100">IMPRESSIVA</span>
      <span className="h-2 w-2 bg-flare" aria-hidden />
    </Link>
  );
}

export default function Nav() {
  const { isAuthed, isAdmin, user, logout } = useAuth();
  const [scrolled, setScrolled] = useState(false);
  const [open, setOpen] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 8);
    onScroll();
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

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
    <header className="fixed inset-x-0 top-0 z-50">
      <div
        className={`transition-colors duration-300 ${scrolled ? 'glass' : 'border-b border-transparent'}`}
      >
        <div className="mx-auto flex max-w-[1400px] items-center justify-between px-5 py-4 sm:px-8">
          <Brand />

          <nav className="hidden items-center gap-9 md:flex">
            {NAV_ITEMS.map((item, i) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === ROUTES.home}
                className={({ isActive }) =>
                  `spec text-xs uppercase tracking-[0.2em] transition-colors ${
                    isActive ? 'text-flare' : 'text-paper-100/60 hover:text-paper-100'
                  }`
                }
              >
                <span className="text-paper-100/25">{String(i + 1).padStart(2, '0')} </span>
                {item.label}
              </NavLink>
            ))}
          </nav>

          <div className="hidden items-center gap-5 md:flex">
            {isAuthed ? (
              <>
                {isAdmin ? (
                  <Link
                    to={ROUTES.admin}
                    className="spec text-xs uppercase tracking-[0.2em] text-paper-100/60 transition-colors hover:text-paper-100"
                  >
                    Admin
                  </Link>
                ) : null}
                <Link
                  to={ROUTES.account}
                  className="spec text-xs uppercase tracking-[0.2em] text-paper-100 link-wipe"
                >
                  {user?.name?.split(' ')[0] || 'Account'}
                </Link>
                <button
                  onClick={handleLogout}
                  className="spec pressable text-xs uppercase tracking-[0.2em] text-paper-100/50 hover:text-flare"
                >
                  Out
                </button>
              </>
            ) : (
              <>
                <Link
                  to={ROUTES.login}
                  className="spec text-xs uppercase tracking-[0.2em] text-paper-100/60 transition-colors hover:text-paper-100"
                >
                  Log In
                </Link>
                <Link
                  to={ROUTES.signup}
                  className="spec pressable bg-flare px-5 py-2.5 text-xs font-700 uppercase tracking-[0.2em] text-white hover:bg-flare-deep"
                >
                  Start a Job
                </Link>
              </>
            )}
          </div>

          <button
            onClick={() => setOpen((v) => !v)}
            className="pressable text-paper-100 md:hidden"
            aria-label="Toggle menu"
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
            <div className="flex gap-3 py-4">
              {isAuthed ? (
                <>
                  <Link
                    to={ROUTES.account}
                    onClick={() => setOpen(false)}
                    className="spec flex-1 border border-paper-100/20 py-3 text-center text-xs uppercase tracking-[0.2em] text-paper-100"
                  >
                    Account
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
