import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link, NavLink, useLocation, useNavigate } from 'react-router-dom';
import { ArrowUpLeft, LogOut, Menu, Plus, Search, X } from 'lucide-react';
import { useAuth } from '@hooks/useAuth.js';
import { MODIFIER, useHotkeys } from '@hooks/useHotkeys.js';
import { ROUTES } from '@constants/routes.js';
import { initials } from '@utils/format.js';
import SplitRail from '@taylorurl/split-rail';
import Picture from '@components/ui/Picture.jsx';
import CommandPalette from '@components/panel/CommandPalette.jsx';

// The panels are their own site view: no marketing nav, footer, or social
// rail. A narrow tool sidebar and a Cmd/Ctrl+K palette; the storefront
// stays one click away.

function PanelNav({ items, onNavigate, className = '' }) {
  return (
    <nav className={className} aria-label="Panel">
      {items.map((item) => (
        <NavLink
          key={item.to}
          to={item.to}
          end={item.end}
          onClick={onNavigate}
          className={({ isActive }) =>
            `group mx-3 flex items-center gap-3 rounded-md px-3 py-2 transition-colors ${
              isActive
                ? 'bg-flare/10 text-paper-100 shadow-nav-active'
                : 'text-paper-100/55 hover:bg-paper-100/5 hover:text-paper-100'
            }`
          }
        >
          {({ isActive }) => (
            <>
              <item.icon
                className={`h-4 w-4 shrink-0 transition-colors ${isActive ? 'text-flare' : 'text-paper-100/40 group-hover:text-paper-100/70'}`}
                strokeWidth={1.8}
              />
              <span className="text-[13px] font-500">{item.label}</span>
            </>
          )}
        </NavLink>
      ))}
    </nav>
  );
}

function UserChip({ user, onLogout }) {
  return (
    <div className="flex items-center gap-3">
      <span className="grid h-8 w-8 shrink-0 place-items-center rounded-full border border-flare/40 bg-flare/10 text-[11px] font-700 text-flare">
        {initials(user.name) || '?'}
      </span>
      <div className="min-w-0 flex-1">
        <p className="truncate text-[13px] font-600 text-paper-100">{user.name}</p>
        <p className="truncate text-[11px] text-paper-100/40">{user.email}</p>
      </div>
      <button
        onClick={onLogout}
        className="pressable shrink-0 rounded-md p-2 text-paper-100/40 transition-colors hover:bg-paper-100/5 hover:text-flare"
        aria-label="Log Out"
        title="Log Out"
      >
        <LogOut className="h-4 w-4" />
      </button>
    </div>
  );
}

export default function PanelShell({ label, scope, navItems, newOrderTo, children }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const [open, setOpen] = useState(false);
  const [paletteOpen, setPaletteOpen] = useState(false);

  useEffect(() => {
    window.scrollTo(0, 0);
    setOpen(false);
  }, [pathname]);

  const handleLogout = useCallback(() => {
    logout();
    navigate(ROUTES.home);
  }, [logout, navigate]);

  const openPalette = useCallback(() => setPaletteOpen((v) => !v), []);
  const closePalette = useCallback(() => setPaletteOpen(false), []);

  useHotkeys({ onPalette: openPalette });

  const paletteActions = useMemo(() => {
    const rows = navItems.map((item) => ({
      icon: item.icon,
      label: `Go to ${item.label}`,
      run: () => navigate(item.to),
    }));
    if (newOrderTo) {
      rows.unshift({ icon: Plus, label: 'New Order', run: () => navigate(newOrderTo) });
    }
    rows.push(
      { icon: ArrowUpLeft, label: 'Back to Site', run: () => navigate(ROUTES.home) },
      { icon: LogOut, label: 'Log Out', run: handleLogout },
    );
    return rows;
  }, [navItems, newOrderTo, navigate, handleLogout]);

  const searchButton = (
    <button
      onClick={openPalette}
      aria-expanded={paletteOpen}
      aria-haspopup="dialog"
      aria-controls="command-palette"
      className="pressable mx-3 mb-1 mt-3 flex items-center gap-2 rounded-md border border-paper-100/12 bg-ink-950 px-3 py-2 text-[13px] text-paper-100/45 transition-colors hover:border-paper-100/25 hover:text-paper-100/70"
    >
      <Search className="h-3.5 w-3.5" />
      Search
      <kbd className="spec ml-auto rounded border border-paper-100/15 px-2 py-px text-[9px] text-paper-100/40">
        {MODIFIER}K
      </kbd>
    </button>
  );

  const sidebarFooter = (
    <div className="border-t border-paper-100/8 p-3">
      <Link
        to={ROUTES.home}
        className="pressable mb-3 flex items-center gap-2 px-1 text-xs text-paper-100/45 transition-colors hover:text-paper-100"
      >
        <ArrowUpLeft className="h-3.5 w-3.5" />
        Back to Site
      </Link>
      <UserChip user={user} onLogout={handleLogout} />
    </div>
  );

  return (
    <div className="relative min-h-dvh overflow-x-clip bg-ink-950 text-[14px]">
      {/* Desktop sidebar */}
      <aside className="fixed inset-y-0 left-0 z-sticky hidden w-56 flex-col border-r border-paper-100/8 bg-ink-900 lg:flex">
        <div className="flex items-center gap-3 px-4 pb-2 pt-4">
          <Link to={ROUTES.home} aria-label="Impressiva Printing Home" className="shrink-0">
            <Picture
              src="/logo"
              alt="Impressiva Printing"
              width="1200"
              height="410"
              widths={[560, 1200]}
              sizes="100px"
              className="h-7 w-auto"
            />
          </Link>
          <span className="ml-auto rounded border border-paper-100/12 px-2 py-1 text-[10px] font-600 uppercase tracking-wider text-paper-100/50">
            {label}
          </span>
        </div>
        {searchButton}
        <PanelNav items={navItems} className="flex-1 space-y-1 overflow-y-auto py-2" />
        {sidebarFooter}
      </aside>

      {/* Mobile top bar + drawer */}
      <header className="sticky top-0 z-sticky lg:hidden">
        <div className="border-b border-paper-100/8 bg-ink-900">
          <div className="flex items-center justify-between px-4 py-3">
            <div className="flex items-center gap-3">
              <Link to={ROUTES.home} aria-label="Impressiva Printing Home">
                <Picture
                  src="/logo"
                  alt="Impressiva Printing"
                  width="1200"
                  height="410"
                  widths={[560, 1200]}
                  sizes="100px"
                  className="h-7 w-auto"
                />
              </Link>
              <span className="rounded border border-paper-100/12 px-2 py-1 text-[10px] font-600 uppercase tracking-wider text-paper-100/50">
                {label}
              </span>
            </div>
            <div className="flex items-center gap-1">
              <button
                onClick={openPalette}
                className="pressable rounded-md p-2 text-paper-100/60 transition-colors hover:bg-paper-100/5 hover:text-paper-100"
                aria-label="Search"
              >
                <Search className="h-[18px] w-[18px]" />
              </button>
              <button
                onClick={() => setOpen((v) => !v)}
                className="pressable rounded-md p-2 text-paper-100"
                aria-label="Toggle Panel Menu"
                aria-expanded={open}
              >
                {open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
              </button>
            </div>
          </div>
        </div>
        {open ? (
          <div className="animate-pop-in border-b border-paper-100/8 bg-ink-900 shadow-drawer">
            <PanelNav items={navItems} onNavigate={() => setOpen(false)} className="py-2" />
            {sidebarFooter}
          </div>
        ) : null}
      </header>

      <main className="lg:pl-56">{children}</main>

      {/* The panels carry no marketing footer, so this one holds the rail
          alone, in the shell's own ground and ink, lined up with the content
          column. */}
      <footer className="bg-ink-950 text-paper-100 lg:pl-56">
        <SplitRail />
      </footer>

      <CommandPalette
        open={paletteOpen}
        onClose={closePalette}
        scope={scope}
        user={user}
        actions={paletteActions}
      />
    </div>
  );
}
