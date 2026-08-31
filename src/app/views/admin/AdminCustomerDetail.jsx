import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { Check, UserX } from 'lucide-react';
import { useStoreQuery } from '@hooks/useStoreQuery.js';
import { store } from '@data/store.js';
import { ACTIVE_STATUSES } from '@constants/orders.js';
import { ROUTES, adminOrderPath } from '@constants/routes.js';
import { formatDate } from '@utils/format.js';

import PanelPage from '@components/panel/PanelPage.jsx';
import { PanelButton } from '@components/panel/ui.jsx';
import OrderList from '@components/panel/OrderList.jsx';
import {
  AREA,
  EmptyState,
  PanelCard,
  PanelError,
  PanelLoading,
  SectionTitle,
  SpecList,
  StatGrid,
} from '@components/panel/ui.jsx';

export default function AdminCustomerDetail() {
  const { customerId } = useParams();
  const navigate = useNavigate();
  const {
    data,
    loading,
    error: loadError,
    reload,
  } = useStoreQuery(async () => {
    const [customer, orders] = await Promise.all([
      store.findUserById(customerId),
      store.getOrdersForUser(customerId),
    ]);
    return {
      customer,
      orders: [...orders].sort((a, b) => b.updatedAt.localeCompare(a.updatedAt)),
    };
  }, [customerId]);

  const customer = data?.customer;
  const [note, setNote] = useState('');
  const [noteSaved, setNoteSaved] = useState(false);
  const [error, setError] = useState('');

  // The note draft follows whatever the database holds for the customer on
  // show — including when the route param changes without a remount.
  useEffect(() => {
    setNote(customer?.shopNote || '');
    setNoteSaved(false);
  }, [customer]);

  if (loading || loadError) {
    return (
      <PanelPage context="Customers" title="Customer">
        {loading ? <PanelLoading /> : <PanelError message={loadError} onRetry={reload} />}
      </PanelPage>
    );
  }

  if (!customer || customer.role !== 'customer') {
    return (
      <PanelPage context="Customers" title="Not Found">
        <EmptyState title="This account doesn't exist any more.">
          <PanelButton to={ROUTES.adminCustomers} variant="outline" size="sm">
            Back to Customers
          </PanelButton>
        </EmptyState>
      </PanelPage>
    );
  }

  const orders = data.orders;
  const fileCount = orders.reduce((sum, o) => sum + o.files.length, 0);
  const stats = [
    { value: orders.length, label: 'Orders' },
    { value: orders.filter((o) => ACTIVE_STATUSES.includes(o.status)).length, label: 'Active' },
    { value: fileCount, label: 'Files' },
  ];

  const saveNote = async (e) => {
    e.preventDefault();
    setError('');
    try {
      await store.saveShopNote(customer.id, note.trim());
      setNoteSaved(true);
    } catch (err) {
      setError(err.message);
    }
  };

  const handleRemove = async () => {
    if (
      !window.confirm(`Remove ${customer.name} and all of their orders? This cannot be undone.`)
    ) {
      return;
    }
    setError('');
    try {
      await store.removeUser(customer.id);
      navigate(ROUTES.adminCustomers, { replace: true });
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <PanelPage context="Customers" title={customer.name} meta={customer.company || customer.email}>
      <div className="grid gap-5 lg:grid-cols-[1.5fr_1fr]">
        <div className="space-y-5">
          <StatGrid stats={stats} />
          <section>
            <SectionTitle aside={orders.length}>Orders</SectionTitle>
            <OrderList
              orders={orders}
              getPath={adminOrderPath}
              empty={{ title: 'No orders yet.' }}
            />
          </section>
        </div>

        <div className="space-y-5 self-start">
          <PanelCard title="Contact">
            <SpecList
              items={[
                { k: 'Email', value: customer.email },
                { k: 'Phone', value: customer.phone || '-' },
                { k: 'Company', value: customer.company || '-' },
                { k: 'Joined', value: formatDate(customer.createdAt) },
              ]}
            />
          </PanelCard>

          <PanelCard title="Notes" aside="Internal">
            <form onSubmit={saveNote}>
              <textarea
                rows={4}
                className={AREA}
                placeholder="Preferred stocks, billing details, proof preferences…"
                value={note}
                onChange={(e) => {
                  setNote(e.target.value);
                  setNoteSaved(false);
                }}
              />
              <div className="mt-3 flex items-center gap-3">
                <PanelButton as="button" type="submit" variant="outline" size="sm">
                  Save Note
                </PanelButton>
                {noteSaved ? (
                  <span className="flex items-center gap-1 text-xs text-proc-y">
                    <Check className="h-3.5 w-3.5" /> Saved
                  </span>
                ) : null}
              </div>
            </form>
          </PanelCard>

          <PanelCard title="Account">
            <p className="text-xs leading-relaxed text-paper-100/45">
              Removing this customer deletes their login, orders, and files from the shop&apos;s
              database.
            </p>
            <button
              onClick={handleRemove}
              className="pressable mt-3 inline-flex items-center gap-2 rounded-md border border-paper-100/15 px-3 py-2 text-xs font-500 text-paper-100/60 transition-colors hover:border-flare/50 hover:text-flare"
            >
              <UserX className="h-3.5 w-3.5" /> Remove Customer
            </button>
            {error ? (
              <p className="mt-3 rounded-md border border-flare/30 bg-flare/10 px-3 py-2 text-xs text-paper-100">
                {error}
              </p>
            ) : null}
          </PanelCard>
        </div>
      </div>
    </PanelPage>
  );
}
