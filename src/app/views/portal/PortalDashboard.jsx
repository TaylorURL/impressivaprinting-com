import { Link } from 'react-router-dom';
import { Plus } from 'lucide-react';
import { useAuth } from '@hooks/useAuth.js';
import { useStoreQuery } from '@hooks/useStoreQuery.js';
import { store } from '@data/store.js';
import { ACTIVE_STATUSES, ORDER_STATUSES, PIPELINE_STEPS } from '@constants/orders.js';
import { ROUTES, portalOrderPath } from '@constants/routes.js';
import { SITE } from '@constants/site.js';

import PanelPage from '@components/panel/PanelPage.jsx';
import { PanelButton } from '@components/panel/ui.jsx';
import OrderList from '@components/panel/OrderList.jsx';
import {
  EmptyState,
  PanelCard,
  PanelError,
  PanelLoading,
  SectionTitle,
  SpecList,
  StatGrid,
  StatusChip,
} from '@components/panel/ui.jsx';

const ATTENTION_CTA = {
  'awaiting-artwork': 'Upload Artwork',
  proofing: 'Review Proof',
};

// Index-aligned with PIPELINE_STEPS. Reference lines, not sales copy.
const PIPELINE_NOTES = [
  'Upload print-ready files',
  'Prepress checks them',
  'Approve before press',
  'Printing',
  'Pickup at the studio',
  'Closed',
];

function AttentionRow({ order }) {
  return (
    <Link
      to={portalOrderPath(order.id)}
      className="flex items-center gap-3 border-b border-paper-100/8 px-4 py-3 transition-colors last:border-b-0 hover:bg-ink-850"
    >
      <span className="spec hidden w-[85px] shrink-0 text-[11px] text-flare sm:block">
        {order.number}
      </span>
      <div className="min-w-0 flex-1">
        <p className="truncate text-[13px] font-600 text-paper-100">
          {order.product.name}
          {order.qty ? <span className="font-400 text-paper-100/50"> ×{order.qty}</span> : null}
        </p>
        <p className="truncate text-xs text-paper-100/45">
          {ORDER_STATUSES[order.status].customerHint}
        </p>
      </div>
      <StatusChip status={order.status} pulse className="hidden shrink-0 md:inline-flex" />
      <span className="shrink-0 rounded-md border border-flare/40 bg-flare/10 px-3 py-1 text-xs font-600 text-flare">
        {ATTENTION_CTA[order.status]}
      </span>
    </Link>
  );
}

export default function PortalDashboard() {
  const { user } = useAuth();
  const { data, loading, error, reload } = useStoreQuery(
    () => store.getOrdersForUser(user.id),
    [user.id],
  );

  const orders = data || [];
  const sorted = [...orders].sort((a, b) => b.updatedAt.localeCompare(a.updatedAt));
  const attention = sorted.filter(
    (o) => o.status === 'awaiting-artwork' || o.status === 'proofing',
  );
  const stats = [
    {
      value: orders.filter((o) => ACTIVE_STATUSES.includes(o.status)).length,
      label: 'Active',
    },
    { value: orders.filter((o) => o.status === 'in-production').length, label: 'On Press' },
    { value: orders.filter((o) => o.status === 'ready').length, label: 'Ready' },
    { value: orders.filter((o) => o.status === 'completed').length, label: 'Completed' },
  ];

  return (
    <PanelPage
      title="Dashboard"
      meta={user.company || user.email}
      actions={
        <PanelButton to={ROUTES.portalNewOrder} variant="flare" size="sm">
          <Plus className="h-3.5 w-3.5" /> New Order
        </PanelButton>
      }
    >
      <div className="grid gap-5 lg:grid-cols-[1.6fr_1fr]">
        <div className="space-y-6">
          {loading ? (
            <PanelLoading />
          ) : error ? (
            <PanelError message={error} onRetry={reload} />
          ) : orders.length === 0 ? (
            <EmptyState
              title="No orders yet."
              body="Place an order, upload your artwork, and approve the proof here. Every job is quoted before it runs."
            >
              <PanelButton to={ROUTES.portalNewOrder} variant="flare" size="sm">
                <Plus className="h-3.5 w-3.5" /> New Order
              </PanelButton>
            </EmptyState>
          ) : (
            <>
              <StatGrid stats={stats} />

              {attention.length > 0 ? (
                <section>
                  <SectionTitle aside={attention.length}>Action Needed</SectionTitle>
                  <div className="overflow-hidden rounded-lg border border-flare/25 bg-ink-900 shadow-card-flare">
                    {attention.map((order) => (
                      <AttentionRow key={order.id} order={order} />
                    ))}
                  </div>
                </section>
              ) : null}

              <section>
                <SectionTitle
                  aside={
                    <Link
                      to={ROUTES.portalOrders}
                      className="text-paper-100/50 hover:text-paper-100"
                    >
                      View All
                    </Link>
                  }
                >
                  Recent Orders
                </SectionTitle>
                <OrderList orders={sorted.slice(0, 6)} getPath={portalOrderPath} />
              </section>
            </>
          )}
        </div>

        <div className="space-y-5 self-start">
          <PanelCard title="How Orders Move">
            <ol>
              {PIPELINE_STEPS.map((step, i) => (
                <li
                  key={step}
                  className="flex items-baseline gap-3 border-b border-paper-100/8 py-2 last:border-b-0"
                >
                  <span className="spec w-4 shrink-0 text-[10px] text-flare">{i + 1}</span>
                  <span className="w-16 shrink-0 text-xs font-500 text-paper-100/75">{step}</span>
                  <span className="min-w-0 text-xs text-paper-100/50">{PIPELINE_NOTES[i]}</span>
                </li>
              ))}
            </ol>
          </PanelCard>

          <PanelCard title="The Shop">
            <SpecList
              items={[
                { k: 'Phone', value: SITE.phone },
                { k: 'Email', value: SITE.email },
                { k: 'Address', value: SITE.address },
                { k: 'Hours', value: SITE.hours },
              ]}
            />
            <Link
              to={ROUTES.contact}
              className="mt-3 inline-block text-xs font-500 link-wipe text-flare"
            >
              Contact Page
            </Link>
          </PanelCard>
        </div>
      </div>
    </PanelPage>
  );
}
