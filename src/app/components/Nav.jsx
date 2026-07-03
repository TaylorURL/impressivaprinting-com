import { useEffect, useState } from 'react';
import { Link, NavLink, useNavigate } from 'react-router-dom';
import { LogOut, Menu, ShieldCheck, User, X } from 'lucide-react';
import { NAV_ITEMS, ROUTES } from '@constants/routes.js';
import { useAuth } from '@hooks/useAuth.js';
import Button from '@components/Button.jsx';

function Brand() {
  return (
    <Link to={ROUTES.home} className="group flex items-center gap-2.5">
      <span className="grid h-9 w-9 place-items-center rounded-xl street-gradient text-ink-950 shadow-neon-magenta">
        <span className="spray text-lg leading-none">IP</span>
      </span>
      <span className="spray text-xl tracking-tight text-white">
        Impressiva<span className="text-neon-magenta">.</span>
      </span>
    </Link>
  );
}

function navLinkClass({ isActive }) {
  return [
    'relative font-head text-sm font-600 uppercase tracking-wide transition-colors duration-200',
    isActive ? 'text-white' : 'text-white/55 hover:text-white',
  ].join(' ');
}

export default function Nav() {
  const { isAuthed, isAdmin, user, logout } = useAuth();
  const [scrolled, setScrolled] = useState(false);
  const [open, setOpen] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 12);
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
    <header className="fixed inset-x-0 top-0 z-50 px-4 pt-4">
      <div
        className={`mx-auto flex max-w-6xl items-center justify-between rounded-2xl px-4 py-3 transition-all duration-300 ease-street sm:px-6 ${
          scrolled ? 'glass glass-sheen' : 'border border-transparent'
        }`}
      >
        <Brand />

        <nav className="hidden items-center gap-8 md:flex">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={navLinkClass}
              end={item.to === ROUTES.home}
            >
              {item.label}
            </NavLink>
          ))}
        </nav>

        <div className="hidden items-center gap-3 md:flex">
          {isAuthed ? (
            <>
              {isAdmin ? (
                <Button to={ROUTES.admin} variant="outline" size="sm">
                  <ShieldCheck className="h-4 w-4" /> Admin
                </Button>
              ) : null}
              <Button to={ROUTES.account} variant="glass" size="sm">
                <User className="h-4 w-4" /> {user?.name?.split(' ')[0] || 'Account'}
              </Button>
              <button
                onClick={handleLogout}
                className="pressable grid h-10 w-10 place-items-center rounded-full border border-white/15 text-white/60 hover:border-magenta/60 hover:text-white"
                aria-label="Log out"
              >
                <LogOut className="h-4 w-4" />
              </button>
            </>
          ) : (
            <>
              <Button to={ROUTES.login} variant="ghost" size="sm">
                Log In
              </Button>
              <Button to={ROUTES.signup} variant="primary" size="sm">
                Start a Job
              </Button>
            </>
          )}
        </div>

        <button
          onClick={() => setOpen((v) => !v)}
          className="pressable grid h-10 w-10 place-items-center rounded-xl glass text-white md:hidden"
          aria-label="Toggle menu"
          aria-expanded={open}
        >
          {open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
        </button>
      </div>

      {/* Mobile sheet */}
      {open ? (
        <div className="mt-3 md:hidden">
          <div className="glass glass-sheen mx-auto flex max-w-6xl flex-col gap-1 rounded-2xl p-4">
            {NAV_ITEMS.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === ROUTES.home}
                onClick={() => setOpen(false)}
                className={({ isActive }) =>
                  `rounded-xl px-4 py-3 font-head text-sm font-600 uppercase tracking-wide transition-colors ${
                    isActive
                      ? 'bg-white/10 text-white'
                      : 'text-white/60 hover:bg-white/5 hover:text-white'
                  }`
                }
              >
                {item.label}
              </NavLink>
            ))}
            <div className="mt-2 grid grid-cols-2 gap-2">
              {isAuthed ? (
                <>
                  <Button
                    to={ROUTES.account}
                    variant="glass"
                    size="sm"
                    onClick={() => setOpen(false)}
                  >
                    <User className="h-4 w-4" /> Account
                  </Button>
                  {isAdmin ? (
                    <Button
                      to={ROUTES.admin}
                      variant="outline"
                      size="sm"
                      onClick={() => setOpen(false)}
                    >
                      <ShieldCheck className="h-4 w-4" /> Admin
                    </Button>
                  ) : (
                    <Button
                      to={ROUTES.products}
                      variant="outline"
                      size="sm"
                      onClick={() => setOpen(false)}
                    >
                      Products
                    </Button>
                  )}
                  <button
                    onClick={handleLogout}
                    className="pressable col-span-2 rounded-full border border-white/15 py-3 font-head text-sm font-600 uppercase tracking-wide text-white/70 hover:border-magenta/60 hover:text-white"
                  >
                    Log Out
                  </button>
                </>
              ) : (
                <>
                  <Button
                    to={ROUTES.login}
                    variant="outline"
                    size="sm"
                    onClick={() => setOpen(false)}
                  >
                    Log In
                  </Button>
                  <Button
                    to={ROUTES.signup}
                    variant="primary"
                    size="sm"
                    onClick={() => setOpen(false)}
                  >
                    Start a Job
                  </Button>
                </>
              )}
            </div>
          </div>
        </div>
      ) : null}
    </header>
  );
}
