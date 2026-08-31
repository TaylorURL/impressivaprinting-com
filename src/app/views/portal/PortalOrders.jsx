import { useState } from 'react';
import { Plus } from 'lucide-react';
import { useAuth } from '@hooks/useAuth.js';
import { useStoreQuery } from '@hooks/useStoreQuery.js';
import { store } from '@data/store.js';
import { ACTIVE_STATUSES, CLOSED_STATUSES } from '@constants/orders.js';
import { ROUTES, portalOrderPath } from '@constants/routes.js';

import PanelPage from '@components/panel/PanelPage.jsx';
import OrderList from '@components/panel/OrderList.jsx';
import { FilterTabs, PanelButton, PanelError, PanelLoading } from '@components/panel/ui.jsx';

const FILTERS = {
  all: () => true,
  attention: (o) => o.status === 'awaiting-artwork' || o.status === 'proofing',
  active: (o) => ACTIVE_STATUSES.includes(o.status),
  closed: (o) => CLOSED_STATUSES.includes(o.status),
};

export default function PortalOrders() {
  const { user } = useAuth();
  const [filter, setFilter] = useState('all');
  const { data, loading, error, reload } = useStoreQuery(
    () => store.getOrdersForUser(user.id),
    [user.id],
  );

  const orders = [...(data || [])].sort((a, b) => b.updatedAt.localeCompare(a.updatedAt));

  const options = [
    { value: 'all', label: 'All', count: orders.length },
    { value: 'attention', label: 'Needs You', count: orders.filter(FILTERS.attention).length },
    { value: 'active', label: 'Active', count: orders.filter(FILTERS.active).length },
    { value: 'closed', label: 'Closed', count: orders.filter(FILTERS.closed).length },
  ];

  return (
    <PanelPage
      title="Orders"
      meta={loading ? '…' : `${orders.length} total`}
      actions={
        <PanelButton to={ROUTES.portalNewOrder} variant="flare" size="sm">
          <Plus className="h-3.5 w-3.5" /> New Order
        </PanelButton>
      }
    >
      <div className="mb-4">
        <FilterTabs options={options} value={filter} onChange={setFilter} />
      </div>
      {loading ? (
        <PanelLoading />
      ) : error ? (
        <PanelError message={error} onRetry={reload} />
      ) : (
        <OrderList
          orders={orders.filter(FILTERS[filter])}
          getPath={portalOrderPath}
          empty={{ title: 'No orders in this view.' }}
        />
      )}
    </PanelPage>
  );
}
