import { useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { Trash2 } from 'lucide-react';
import { useStoreQuery } from '@hooks/useStoreQuery.js';
import { store } from '@data/store.js';
import { ORDER_STATUSES, SHOP_ACTIONS } from '@constants/orders.js';
import { ROUTES, adminCustomerPath } from '@constants/routes.js';
import { buildFileRecords } from '@utils/files.js';
import { formatDate } from '@utils/format.js';

import PanelPage from '@components/panel/PanelPage.jsx';
import OrderStepper from '@components/panel/OrderStepper.jsx';
import EventTimeline from '@components/panel/EventTimeline.jsx';
import ArtworkTile from '@components/panel/ArtworkTile.jsx';
import NoteComposer from '@components/panel/NoteComposer.jsx';
import OrderActions from '@components/panel/OrderActions.jsx';
import UploadDrop from '@components/panel/UploadDrop.jsx';
import {
  EmptyState,
  LABEL,
  PanelCard,
  PanelError,
  PanelLoading,
  SpecList,
  StatusChip,
  PanelButton,
} from '@components/panel/ui.jsx';

// While a job sits in review or proofing, the shop can attach proof files
// for the customer to check before approving.
const PROOF_STATUSES = ['in-review', 'proofing'];

export default function AdminOrderDetail() {
  const { orderId } = useParams();
  const navigate = useNavigate();
  const [error, setError] = useState('');
  const {
    data,
    loading,
    error: loadError,
    reload,
  } = useStoreQuery(async () => {
    const order = await store.getOrder(orderId);
    const customer = order ? await store.findUserById(order.userId) : null;
    return { order, customer };
  }, [orderId]);

  if (loading || loadError) {
    return (
      <PanelPage context="Orders" title="Order">
        {loading ? <PanelLoading /> : <PanelError message={loadError} onRetry={reload} />}
      </PanelPage>
    );
  }

  const { order, customer } = data;

  if (!order) {
    return (
      <PanelPage context="Orders" title="Not Found">
        <EmptyState title="This order doesn't exist any more.">
          <PanelButton to={ROUTES.adminOrders} variant="outline" size="sm">
            Back to Orders
          </PanelButton>
        </EmptyState>
      </PanelPage>
    );
  }

  const meta = ORDER_STATUSES[order.status];

  const handleAction = async (actionId, note) => {
    setError('');
    try {
      await store.applyOrderAction(order.id, actionId, note);
    } catch (err) {
      setError(err.message);
    }
    reload();
  };

  const handleProofFiles = async (fileList) => {
    setError('');
    const { records, error: problem } = await buildFileRecords(fileList);
    if (problem) setError(problem);
    try {
      for (const record of records) {
        await store.addArtwork(order.id, record, 'shop');
      }
    } catch (err) {
      setError(err.message);
    }
    reload();
  };

  const handleRemoveProof = async (fileId) => {
    setError('');
    try {
      await store.removeArtwork(order.id, fileId, 'shop');
    } catch (err) {
      setError(err.message);
    }
    reload();
  };

  const handleNote = async (note) => {
    setError('');
    try {
      await store.addOrderNote(order.id, 'shop', note);
    } catch (err) {
      setError(err.message);
    }
    reload();
  };

  const handleDelete = async () => {
    if (!window.confirm('Delete this order and its files for good?')) return;
    try {
      await store.removeOrder(order.id);
      navigate(ROUTES.adminOrders, { replace: true });
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <PanelPage
      context={`Orders / ${order.number}`}
      title={
        <>
          {order.product.name}
          {order.qty ? <span className="text-paper-100/50"> ×{order.qty}</span> : null}
        </>
      }
      meta={<StatusChip status={order.status} />}
    >
      <div className="grid gap-5 lg:grid-cols-[1.5fr_1fr]">
        <div className="space-y-5">
          <PanelCard title="Status" aside={`Placed ${formatDate(order.createdAt)}`}>
            <OrderStepper status={order.status} />
            <p className="mt-3 text-xs text-paper-100/55">{meta.shopHint}</p>
            {SHOP_ACTIONS[order.status]?.length ? (
              <div className="mt-4 border-t border-paper-100/10 pt-4">
                <OrderActions actionIds={SHOP_ACTIONS[order.status]} onApply={handleAction} />
              </div>
            ) : null}
            {error ? (
              <p className="mt-3 rounded-md border border-flare/30 bg-flare/10 px-3 py-2 text-xs text-paper-100">
                {error}
              </p>
            ) : null}
          </PanelCard>

          <PanelCard title="Artwork & Proofs" aside={`${order.files.length} files`}>
            {order.files.length > 0 ? (
              <div className="grid gap-4 sm:grid-cols-2">
                {order.files.map((file) => (
                  <ArtworkTile
                    key={file.id}
                    file={file}
                    downloadable
                    onRemove={file.uploadedBy === 'shop' ? handleRemoveProof : undefined}
                  />
                ))}
              </div>
            ) : (
              <p className="text-xs text-paper-100/50">No files from the customer yet.</p>
            )}
            {PROOF_STATUSES.includes(order.status) ? (
              <div className="mt-4 border-t border-paper-100/10 pt-4">
                <p className={LABEL}>Attach a Proof</p>
                <UploadDrop onFiles={handleProofFiles} compact />
              </div>
            ) : null}
          </PanelCard>
        </div>

        <div className="space-y-5 self-start">
          <PanelCard title="Customer">
            {customer ? (
              <>
                <SpecList
                  items={[
                    { k: 'Name', value: customer.name },
                    { k: 'Company', value: customer.company || '-' },
                    { k: 'Email', value: customer.email },
                    { k: 'Phone', value: customer.phone || '-' },
                  ]}
                />
                <Link
                  to={adminCustomerPath(customer.id)}
                  className="mt-3 inline-block text-xs font-500 link-wipe text-flare"
                >
                  View Customer
                </Link>
              </>
            ) : (
              <p className="text-xs text-paper-100/50">This customer&apos;s account was removed.</p>
            )}
          </PanelCard>

          <PanelCard title="Details" aside={order.product.code}>
            <SpecList
              items={[
                { k: 'Order', value: order.number },
                { k: 'Product', value: order.product.name },
                { k: 'Quantity', value: order.qty ? `×${order.qty}` : '-' },
                { k: 'Size', value: order.size },
                { k: 'Finish', value: order.finish },
                { k: 'Need By', value: order.dueDate ? formatDate(order.dueDate) : '-' },
                { k: 'Placed', value: formatDate(order.createdAt) },
                { k: 'Updated', value: formatDate(order.updatedAt) },
              ]}
            />
            {order.notes ? (
              <p className="mt-3 rounded-md border border-paper-100/10 bg-ink-950/60 px-3 py-2 text-xs leading-relaxed text-paper-100/60">
                {order.notes}
              </p>
            ) : null}
            <button
              onClick={handleDelete}
              className="pressable mt-4 inline-flex w-full items-center gap-2 border-t border-paper-100/8 pt-3 text-xs text-paper-100/40 transition-colors hover:text-flare"
            >
              <Trash2 className="h-3.5 w-3.5" /> Delete Order
            </button>
          </PanelCard>

          <PanelCard title="Activity">
            <EventTimeline
              events={order.events}
              actorNames={{ customer: customer?.name || 'Customer', shop: 'Shop' }}
            />
            <NoteComposer onSend={handleNote} placeholder="Message the customer…" />
          </PanelCard>
        </div>
      </div>
    </PanelPage>
  );
}
