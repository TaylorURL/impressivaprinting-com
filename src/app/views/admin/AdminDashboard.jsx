import { Link } from 'react-router-dom';
import { useStoreQuery } from '@hooks/useStoreQuery.js';
import { store } from '@data/store.js';
import { ROUTES, adminOrderPath } from '@constants/routes.js';
import { formatDateTime, plural } from '@utils/format.js';
import PanelPage from '@components/panel/PanelPage.jsx';
import OrderList from '@components/panel/OrderList.jsx';
import {
  PanelCard,
  PanelError,
  PanelLoading,
  SectionTitle,
  StatGrid,
} from '@components/panel/ui.jsx';

export default function AdminDashboard() {
  const { data, loading, error, reload } = useStoreQuery(async () => {
    const [orders, users] = await Promise.all([store.getOrders(), store.getUsers()]);
    return { orders, users };
  }, []);

  if (loading || error) {
    return (
      <PanelPage title="Dashboard">
        {loading ? <PanelLoading /> : <PanelError message={error} onRetry={reload} />}
      </PanelPage>
    );
  }

  const { orders, users } = data;
  const customers = users.filter((u) => u.role === 'customer');
  const usersById = new Map(users.map((u) => [u.id, u]));
  const customerFor = (order) => usersById.get(order.userId) || null;

  const byStatus = (status) => orders.filter((o) => o.status === status);
  const stats = [
    { value: byStatus('in-review').length, label: 'To Review' },
    { value: byStatus('proofing').length, label: 'Proofs Out' },
    { value: byStatus('in-production').length, label: 'On Press' },
    { value: byStatus('ready').length, label: 'Ready' },
  ];

  // The shop's court: artwork waiting on preflight, oldest first.
  const reviewQueue = byStatus('in-review').sort((a, b) => a.updatedAt.localeCompare(b.updatedAt));

  const activity = orders
    .flatMap((order) => order.events.map((event) => ({ order, event })))
    .sort((a, b) => b.event.at.localeCompare(a.event.at))
    .slice(0, 8);

  return (
    <PanelPage
      title="Dashboard"
      meta={`${orders.length} ${plural(orders.length, 'order')} · ${customers.length} ${plural(customers.length, 'customer')}`}
    >
      <div className="space-y-6">
        <StatGrid stats={stats} />

        <section>
          <SectionTitle
            aside={
              <Link to={ROUTES.adminOrders} className="text-paper-100/50 hover:text-paper-100">
                All Orders
              </Link>
            }
          >
            Review Queue
          </SectionTitle>
          <OrderList
            orders={reviewQueue}
            getPath={adminOrderPath}
            customerFor={customerFor}
            empty={{
              title: 'Nothing waiting on review.',
              body: 'New artwork lands here when a customer uploads it.',
            }}
          />
        </section>

        <div className="grid gap-6 lg:grid-cols-2">
          <section>
            <SectionTitle aside={byStatus('proofing').length}>Proofs Out</SectionTitle>
            <OrderList
              orders={byStatus('proofing')}
              getPath={adminOrderPath}
              customerFor={customerFor}
              empty={{ title: 'No proofs waiting on customers.' }}
            />
          </section>
          <section>
            <SectionTitle aside={byStatus('ready').length}>Ready for Pickup</SectionTitle>
            <OrderList
              orders={byStatus('ready')}
              getPath={adminOrderPath}
              customerFor={customerFor}
              empty={{ title: 'Nothing on the shelf.' }}
            />
          </section>
        </div>

        <PanelCard title="Latest Activity">
          {activity.length === 0 ? (
            <p className="text-xs text-paper-100/45">Nothing yet.</p>
          ) : (
            <ol>
              {activity.map(({ order, event }) => {
                const customer = customerFor(order);
                return (
                  <li
                    key={event.id}
                    className="flex flex-wrap items-baseline gap-x-3 gap-y-1 border-b border-paper-100/8 py-2 last:border-b-0"
                  >
                    <Link
                      to={adminOrderPath(order.id)}
                      className="spec shrink-0 text-[11px] link-wipe text-flare"
                    >
                      {order.number}
                    </Link>
                    <span className="min-w-0 flex-1 text-[13px] text-paper-100/75">
                      {event.label}
                    </span>
                    <span className="shrink-0 text-[11px] text-paper-100/45">
                      {event.actor === 'shop' ? 'Shop' : customer?.name || 'Customer'}
                    </span>
                    <span className="spec shrink-0 text-[10px] text-paper-100/35">
                      {formatDateTime(event.at)}
                    </span>
                  </li>
                );
              })}
            </ol>
          )}
        </PanelCard>
      </div>
    </PanelPage>
  );
}
