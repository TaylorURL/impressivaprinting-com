import { useState } from 'react';
import { Search } from 'lucide-react';
import { useStoreQuery } from '@hooks/useStoreQuery.js';
import { store } from '@data/store.js';
import { ORDER_STATUSES } from '@constants/orders.js';
import { adminOrderPath } from '@constants/routes.js';
import PanelPage from '@components/panel/PanelPage.jsx';
import OrderList from '@components/panel/OrderList.jsx';
import { FIELD, FilterTabs, PanelError, PanelLoading } from '@components/panel/ui.jsx';

export default function AdminOrders() {
  const [filter, setFilter] = useState('all');
  const [query, setQuery] = useState('');
  const { data, loading, error, reload } = useStoreQuery(async () => {
    const [orders, users] = await Promise.all([store.getOrders(), store.getUsers()]);
    return { orders, users };
  }, []);

  const orders = [...(data?.orders || [])].sort((a, b) => b.updatedAt.localeCompare(a.updatedAt));
  const usersById = new Map((data?.users || []).map((u) => [u.id, u]));
  const customerFor = (order) => usersById.get(order.userId) || null;

  const options = [
    { value: 'all', label: 'All', count: orders.length },
    ...Object.entries(ORDER_STATUSES).map(([value, meta]) => ({
      value,
      label: meta.label,
      count: orders.filter((o) => o.status === value).length,
    })),
  ];

  const needle = query.trim().toLowerCase();
  const visible = orders.filter((order) => {
    if (filter !== 'all' && order.status !== filter) return false;
    if (!needle) return true;
    const customer = customerFor(order);
    return [order.number, order.product.name, customer?.name, customer?.email, customer?.company]
      .filter(Boolean)
      .some((field) => field.toLowerCase().includes(needle));
  });

  return (
    <PanelPage title="Orders" meta={loading ? '…' : `${orders.length} total`}>
      <div className="mb-4 space-y-3">
        <div className="relative max-w-xs">
          <Search className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-paper-100/35" />
          <label className="sr-only" htmlFor="order-search">
            Search Orders
          </label>
          <input
            id="order-search"
            type="search"
            name="order-search"
            autoComplete="off"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search orders, customers, products"
            className={`${FIELD} pl-8`}
          />
        </div>
        <FilterTabs options={options} value={filter} onChange={setFilter} />
      </div>
      {loading ? (
        <PanelLoading />
      ) : error ? (
        <PanelError message={error} onRetry={reload} />
      ) : (
        <OrderList
          orders={visible}
          getPath={adminOrderPath}
          customerFor={customerFor}
          empty={{
            title: needle ? 'Nothing matches that search.' : 'No orders in this view.',
          }}
        />
      )}
    </PanelPage>
  );
}
