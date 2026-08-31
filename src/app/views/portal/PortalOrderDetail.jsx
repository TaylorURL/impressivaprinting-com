import { useState } from 'react';
import { useParams } from 'react-router-dom';
import { useAuth } from '@hooks/useAuth.js';
import { useStoreQuery } from '@hooks/useStoreQuery.js';
import { store } from '@data/store.js';
import { CUSTOMER_ACTIONS, ORDER_STATUSES } from '@constants/orders.js';
import { ROUTES } from '@constants/routes.js';
import { buildFileRecords } from '@utils/files.js';
import { formatDate } from '@utils/format.js';

import PanelPage from '@components/panel/PanelPage.jsx';
import OrderStepper from '@components/panel/OrderStepper.jsx';
import EventTimeline from '@components/panel/EventTimeline.jsx';
import ArtworkTile from '@components/panel/ArtworkTile.jsx';
import UploadDrop from '@components/panel/UploadDrop.jsx';
import NoteComposer from '@components/panel/NoteComposer.jsx';
import OrderActions from '@components/panel/OrderActions.jsx';
import {
  EmptyState,
  PanelCard,
  PanelError,
  PanelLoading,
  SpecList,
  StatusChip,
  PanelButton,
} from '@components/panel/ui.jsx';

// Customers can change files while the job is theirs to change — before a
// proof goes out. After that the artwork is locked to what was proofed.
const EDITABLE_STATUSES = ['awaiting-artwork', 'in-review'];

export default function PortalOrderDetail() {
  const { orderId } = useParams();
  const { user } = useAuth();
  const [error, setError] = useState('');
  const {
    data: order,
    loading,
    error: loadError,
    reload,
  } = useStoreQuery(() => store.getOrder(orderId), [orderId]);

  if (loading || loadError) {
    return (
      <PanelPage context="Orders" title="Order">
        {loading ? <PanelLoading /> : <PanelError message={loadError} onRetry={reload} />}
      </PanelPage>
    );
  }

  // Row level security already hides other customers' orders; the ownership
  // check is belt and braces for an admin's own portal view.
  if (!order || order.userId !== user.id) {
    return (
      <PanelPage context="Orders" title="Not Found">
        <EmptyState title="This order doesn't exist or isn't yours.">
          <PanelButton to={ROUTES.portalOrders} variant="outline" size="sm">
            Back to Orders
          </PanelButton>
        </EmptyState>
      </PanelPage>
    );
  }

  const meta = ORDER_STATUSES[order.status];
  const editable = EDITABLE_STATUSES.includes(order.status);

  const handleFiles = async (fileList) => {
    setError('');
    const { records, error: problem } = await buildFileRecords(fileList);
    if (problem) setError(problem);
    try {
      for (const record of records) {
        await store.addArtwork(order.id, record, 'customer');
      }
    } catch (err) {
      setError(err.message);
    }
    reload();
  };

  const handleRemove = async (fileId) => {
    setError('');
    try {
      await store.removeArtwork(order.id, fileId, 'customer');
    } catch (err) {
      setError(err.message);
    }
    reload();
  };

  const handleAction = async (actionId, note) => {
    setError('');
    try {
      await store.applyOrderAction(order.id, actionId, note);
    } catch (err) {
      setError(err.message);
    }
    reload();
  };

  const handleNote = async (note) => {
    setError('');
    try {
      await store.addOrderNote(order.id, 'customer', note);
    } catch (err) {
      setError(err.message);
    }
    reload();
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
            <p className="mt-3 text-xs text-paper-100/55">{meta.customerHint}</p>
            {CUSTOMER_ACTIONS[order.status]?.length ? (
              <div className="mt-4 border-t border-paper-100/10 pt-4">
                <OrderActions actionIds={CUSTOMER_ACTIONS[order.status]} onApply={handleAction} />
              </div>
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
                    onRemove={editable && file.uploadedBy !== 'shop' ? handleRemove : undefined}
                  />
                ))}
              </div>
            ) : (
              <p className="mb-4 text-xs text-paper-100/50">
                No files yet. Upload print-ready artwork to move this job into review.
              </p>
            )}
            {editable ? (
              <div className={order.files.length > 0 ? 'mt-4' : ''}>
                <UploadDrop onFiles={handleFiles} compact />
              </div>
            ) : (
              <p className="spec mt-4 border-t border-paper-100/10 pt-3 text-[10px] uppercase tracking-[0.12em] text-paper-100/35">
                Files are locked while the job is {meta.label.toLowerCase()}
              </p>
            )}
            {error ? (
              <p className="mt-3 rounded-md border border-flare/30 bg-flare/10 px-3 py-2 text-xs text-paper-100">
                {error}
              </p>
            ) : null}
          </PanelCard>
        </div>

        <div className="space-y-5 self-start">
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
              ]}
            />
            {order.notes ? (
              <p className="mt-3 rounded-md border border-paper-100/10 bg-ink-950/60 px-3 py-2 text-xs leading-relaxed text-paper-100/60">
                {order.notes}
              </p>
            ) : null}
          </PanelCard>

          <PanelCard title="Activity">
            <EventTimeline
              events={order.events}
              actorNames={{ customer: 'You', shop: 'Impressiva' }}
            />
            <NoteComposer onSend={handleNote} placeholder="Add a note for the shop…" />
          </PanelCard>
        </div>
      </div>
    </PanelPage>
  );
}
