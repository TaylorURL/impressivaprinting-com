import { Link } from 'react-router-dom';
import { formatDate } from '@utils/format.js';
import { CARD_CLASS, StatusChip, EmptyState } from '@components/panel/ui.jsx';

// One order table for both panels. Passing `customerFor` resolves an order's
// owner and adds the customer column; the portal leaves it out.
export default function OrderList({ orders, getPath, customerFor, empty }) {
  if (orders.length === 0) {
    return <EmptyState title={empty?.title || 'No orders in this view.'} body={empty?.body} />;
  }

  const cols = customerFor
    ? 'sm:grid-cols-[85px_minmax(0,1.3fr)_minmax(0,1fr)_140px_80px]'
    : 'sm:grid-cols-[85px_minmax(0,2fr)_140px_80px]';

  return (
    <div className={`overflow-hidden ${CARD_CLASS}`}>
      <div
        className={`spec hidden gap-3 border-b border-paper-100/8 bg-ink-950/40 px-4 py-2 text-[9px] uppercase tracking-[0.14em] text-paper-100/35 sm:grid ${cols}`}
      >
        <span>Order</span>
        <span>Job</span>
        {customerFor ? <span>Customer</span> : null}
        <span>Status</span>
        <span className="text-right">Updated</span>
      </div>
      {orders.map((order) => {
        const customer = customerFor ? customerFor(order) : null;
        return (
          <Link
            key={order.id}
            to={getPath(order.id)}
            className={`grid grid-cols-[1fr_auto] items-center gap-x-3 gap-y-1 border-b border-paper-100/8 px-4 py-3 transition-colors last:border-b-0 hover:bg-ink-850 sm:gap-3 ${cols}`}
          >
            <span className="spec order-3 text-[10px] text-flare sm:order-none sm:text-[11px]">
              {order.number}
            </span>
            <span className="min-w-0 truncate text-[13px] font-600 text-paper-100">
              {order.product.name}
              {order.qty ? <span className="font-400 text-paper-100/50"> ×{order.qty}</span> : null}
            </span>
            {customerFor ? (
              <span className="order-4 min-w-0 truncate text-xs text-paper-100/60 sm:order-none sm:text-[13px]">
                {customer ? customer.name : 'Deleted customer'}
              </span>
            ) : null}
            <StatusChip
              status={order.status}
              className="order-2 justify-self-end sm:order-none sm:justify-self-start"
            />
            <span className="spec hidden text-right text-[10px] text-paper-100/40 sm:block">
              {formatDate(order.updatedAt)}
            </span>
          </Link>
        );
      })}
    </div>
  );
}
