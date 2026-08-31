import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Search } from 'lucide-react';
import { useStoreQuery } from '@hooks/useStoreQuery.js';
import { store } from '@data/store.js';
import { ACTIVE_STATUSES } from '@constants/orders.js';
import { adminCustomerPath } from '@constants/routes.js';
import { formatDate, initials } from '@utils/format.js';
import PanelPage from '@components/panel/PanelPage.jsx';
import { EmptyState, FIELD, PanelError, PanelLoading } from '@components/panel/ui.jsx';

export default function AdminCustomers() {
  const [query, setQuery] = useState('');
  const { data, loading, error, reload } = useStoreQuery(async () => {
    const [customers, orders] = await Promise.all([store.getCustomers(), store.getOrders()]);
    return customers
      .map((customer) => {
        const theirs = orders.filter((o) => o.userId === customer.id);
        return {
          ...customer,
          orderCount: theirs.length,
          activeCount: theirs.filter((o) => ACTIVE_STATUSES.includes(o.status)).length,
        };
      })
      .sort((a, b) => b.createdAt.localeCompare(a.createdAt));
  }, []);

  const customers = data || [];
  const needle = query.trim().toLowerCase();
  const visible = customers.filter(
    (c) =>
      !needle ||
      [c.name, c.email, c.company].filter(Boolean).some((f) => f.toLowerCase().includes(needle)),
  );

  return (
    <PanelPage title="Customers" meta={loading ? '…' : `${customers.length} total`}>
      <div className="relative mb-4 max-w-xs">
        <Search className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-paper-100/35" />
        <label className="sr-only" htmlFor="customer-search">
          Search Customers
        </label>
        <input
          id="customer-search"
          type="search"
          name="customer-search"
          autoComplete="off"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search name, email, company"
          className={`${FIELD} pl-8`}
        />
      </div>

      {loading ? (
        <PanelLoading />
      ) : error ? (
        <PanelError message={error} onRetry={reload} />
      ) : visible.length === 0 ? (
        <EmptyState
          title={needle ? 'Nothing matches that search.' : 'No customers yet.'}
          body={needle ? undefined : 'Accounts created on the site show up here.'}
        />
      ) : (
        <div className="overflow-hidden rounded-lg border border-paper-100/10 bg-ink-900 shadow-card">
          <div className="spec hidden gap-3 border-b border-paper-100/8 bg-ink-950/40 px-4 py-2 text-[9px] uppercase tracking-[0.14em] text-paper-100/35 sm:grid sm:grid-cols-[minmax(0,1.4fr)_minmax(0,1.2fr)_110px_100px]">
            <span>Customer</span>
            <span>Email</span>
            <span>Orders</span>
            <span className="text-right">Joined</span>
          </div>
          {visible.map((customer) => (
            <Link
              key={customer.id}
              to={adminCustomerPath(customer.id)}
              className="grid grid-cols-[1fr_auto] items-center gap-x-3 gap-y-1 border-b border-paper-100/8 px-4 py-3 transition-colors last:border-b-0 hover:bg-ink-850 sm:grid-cols-[minmax(0,1.4fr)_minmax(0,1.2fr)_110px_100px]"
            >
              <span className="flex min-w-0 items-center gap-3">
                <span className="grid h-7 w-7 shrink-0 place-items-center rounded-full border border-flare/40 bg-flare/10 text-[10px] font-700 text-flare">
                  {initials(customer.name) || '?'}
                </span>
                <span className="min-w-0 truncate text-[13px] font-600 text-paper-100">
                  {customer.name}
                  {customer.company ? (
                    <span className="font-400 text-paper-100/50"> · {customer.company}</span>
                  ) : null}
                </span>
              </span>
              <span className="spec order-3 col-span-2 min-w-0 truncate text-[11px] text-paper-100/45 sm:order-none sm:col-span-1">
                {customer.email}
              </span>
              <span className="spec text-[11px] text-paper-100/60">
                {customer.orderCount}
                {customer.activeCount > 0 ? (
                  <span className="text-flare"> · {customer.activeCount} active</span>
                ) : null}
              </span>
              <span className="spec hidden text-right text-[11px] text-paper-100/40 sm:block">
                {formatDate(customer.createdAt)}
              </span>
            </Link>
          ))}
        </div>
      )}
    </PanelPage>
  );
}
