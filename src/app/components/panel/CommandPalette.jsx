import { useEffect, useMemo, useRef, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { ArrowDown, ArrowUp, CornerDownLeft, Package, Search, UserRound } from 'lucide-react';
import { store } from '@data/store.js';
import { adminCustomerPath, adminOrderPath, portalOrderPath } from '@constants/routes.js';
import { StatusChip } from '@components/panel/ui.jsx';

// Cmd/Ctrl+K. Searches orders (number, product, customer), customers on the
// admin side, and panel actions — arrow keys to move, Enter to jump.
export default function CommandPalette({ open, onClose, scope, user, actions }) {
  const navigate = useNavigate();
  const { pathname } = useLocation();
  const [query, setQuery] = useState('');
  const [active, setActive] = useState(0);
  const [dataset, setDataset] = useState({ orders: [], customers: [] });
  const inputRef = useRef(null);
  const activeRef = useRef(null);
  const openedAt = useRef(pathname);

  useEffect(() => {
    if (!open) return;
    setQuery('');
    setActive(0);
    openedAt.current = pathname;
    inputRef.current?.focus();
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = '';
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  // Orders and customers come from the database, so they're fetched once per
  // open and searched in memory; a stale palette beats a spinner per keystroke.
  useEffect(() => {
    if (!open) return undefined;
    let activeLoad = true;
    const isAdmin = scope === 'admin';
    Promise.all([
      isAdmin ? store.getOrders() : store.getOrdersForUser(user.id),
      isAdmin ? store.getCustomers() : Promise.resolve([]),
    ])
      .then(([orders, customers]) => {
        if (activeLoad) setDataset({ orders, customers });
      })
      .catch(() => {});
    return () => {
      activeLoad = false;
    };
  }, [open, scope, user.id]);

  // If the route changes underneath the palette (a hotkey, a background
  // action), the palette is stale — close it.
  useEffect(() => {
    if (open && pathname !== openedAt.current) onClose();
  }, [open, pathname, onClose]);

  const results = useMemo(() => {
    if (!open) return [];
    const q = query.trim().toLowerCase();
    const match = (...fields) =>
      !q || fields.filter(Boolean).some((f) => f.toLowerCase().includes(q));

    const isAdmin = scope === 'admin';
    const customersById = new Map(dataset.customers.map((c) => [c.id, c]));
    const nameFor = (o) => (isAdmin ? customersById.get(o.userId)?.name : null);

    const orderRows = dataset.orders
      .filter((o) => match(o.number, o.product.name, nameFor(o) || ''))
      .sort((a, b) => b.updatedAt.localeCompare(a.updatedAt))
      .slice(0, q ? 8 : 4)
      .map((o) => ({
        key: `order-${o.id}`,
        group: 'Orders',
        icon: Package,
        label: `${o.number} · ${o.product.name}`,
        sub: nameFor(o),
        status: o.status,
        run: () => navigate(isAdmin ? adminOrderPath(o.id) : portalOrderPath(o.id)),
      }));

    const customerRows = isAdmin
      ? dataset.customers
          .filter((c) => match(c.name, c.email, c.company))
          .slice(0, q ? 6 : 3)
          .map((c) => ({
            key: `customer-${c.id}`,
            group: 'Customers',
            icon: UserRound,
            label: c.name,
            sub: c.email,
            run: () => navigate(adminCustomerPath(c.id)),
          }))
      : [];

    const actionRows = actions
      .filter((a) => match(a.label))
      .map((a) => ({ ...a, key: `action-${a.label}`, group: 'Actions' }));

    return [...orderRows, ...customerRows, ...actionRows];
  }, [open, query, scope, dataset, actions, navigate]);

  useEffect(() => {
    setActive(0);
  }, [query]);

  useEffect(() => {
    activeRef.current?.scrollIntoView({ block: 'nearest' });
  }, [active]);

  if (!open) return null;

  const run = (item) => {
    onClose();
    item.run();
  };

  const onKeyDown = (e) => {
    if (e.key === 'Escape') {
      e.preventDefault();
      onClose();
    } else if (e.key === 'ArrowDown') {
      e.preventDefault();
      setActive((a) => Math.min(a + 1, results.length - 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setActive((a) => Math.max(a - 1, 0));
    } else if (e.key === 'Enter' && results[active]) {
      e.preventDefault();
      run(results[active]);
    }
  };

  let lastGroup = null;

  return (
    <div
      id="command-palette"
      className="animate-overlay-in fixed inset-0 z-modal bg-ink-950/70 backdrop-blur-[2px]"
      onMouseDown={onClose}
      role="dialog"
      aria-modal="true"
      aria-label="Search"
    >
      <div
        className="animate-pop-in mx-4 mt-[10dvh] max-w-lg overflow-hidden rounded-lg border border-paper-100/15 bg-ink-900 shadow-palette sm:mx-auto"
        onMouseDown={(e) => e.stopPropagation()}
      >
        <div className="flex items-center gap-3 border-b border-paper-100/10 px-4">
          <Search className="h-4 w-4 shrink-0 text-paper-100/40" />
          <label className="sr-only" htmlFor="command-palette-search">
            Search
          </label>
          <input
            id="command-palette-search"
            ref={inputRef}
            type="search"
            autoComplete="off"
            autoFocus
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={onKeyDown}
            placeholder={
              scope === 'admin' ? 'Search orders, customers, actions' : 'Search orders, actions'
            }
            className="w-full bg-transparent py-3 text-[13px] text-paper-100 placeholder:text-paper-100/30 outline-none"
          />
          <kbd className="spec shrink-0 rounded border border-paper-100/15 px-2 py-1 text-[9px] text-paper-100/40">
            ESC
          </kbd>
        </div>

        <div className="scroll-contain max-h-[46dvh] overflow-y-auto py-2">
          {results.length === 0 ? (
            <p className="px-4 py-6 text-center text-xs text-paper-100/40">No matches.</p>
          ) : (
            results.map((item, i) => {
              const header =
                item.group !== lastGroup ? (
                  <p className="px-4 pb-1 pt-3 text-[11px] font-600 text-paper-100/40">
                    {item.group}
                  </p>
                ) : null;
              lastGroup = item.group;
              const Icon = item.icon;
              return (
                <div key={item.key}>
                  {header}
                  <button
                    ref={i === active ? activeRef : undefined}
                    onClick={() => run(item)}
                    onMouseMove={() => setActive(i)}
                    className={`flex w-full items-center gap-3 px-4 py-2 text-left transition-colors ${
                      i === active ? 'bg-flare/10 text-paper-100' : 'text-paper-100/70'
                    }`}
                  >
                    <Icon
                      className={`h-3.5 w-3.5 shrink-0 ${i === active ? 'text-flare' : 'text-paper-100/40'}`}
                      strokeWidth={1.8}
                    />
                    <span className="min-w-0 flex-1 truncate text-[13px]">
                      {item.label}
                      {item.sub ? (
                        <span className="ml-2 text-xs text-paper-100/40">{item.sub}</span>
                      ) : null}
                    </span>
                    {item.status ? <StatusChip status={item.status} className="shrink-0" /> : null}
                  </button>
                </div>
              );
            })
          )}
        </div>

        <div className="flex items-center gap-3 border-t border-paper-100/10 px-4 py-2 text-[11px] text-paper-100/35">
          <span className="flex items-center gap-1">
            <ArrowUp className="h-3 w-3" aria-hidden />
            <ArrowDown className="h-3 w-3" aria-hidden />
            Navigate
          </span>
          <span className="flex items-center gap-1">
            <CornerDownLeft className="h-3 w-3" aria-hidden />
            Open
          </span>
        </div>
      </div>
    </div>
  );
}
