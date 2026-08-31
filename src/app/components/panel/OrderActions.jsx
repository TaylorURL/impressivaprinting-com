import { useState } from 'react';
import { ORDER_ACTIONS } from '@constants/orders.js';

import { AREA, LABEL, PanelButton } from '@components/panel/ui.jsx';

// Renders whichever pipeline moves the current status allows. Actions that
// carry a message (change requests, proof notes) expand into an inline
// composer instead of firing straight away.
export default function OrderActions({ actionIds, onApply }) {
  const [pendingId, setPendingId] = useState(null);
  const [note, setNote] = useState('');

  if (actionIds.length === 0) return null;
  const pending = pendingId ? ORDER_ACTIONS[pendingId] : null;

  const trigger = (id) => {
    const action = ORDER_ACTIONS[id];
    if (action.confirm && !window.confirm(action.confirm)) return;
    if (action.notePrompt) {
      setPendingId(id);
      setNote('');
      return;
    }
    onApply(id, '');
  };

  const confirmPending = () => {
    if (pending.noteRequired && !note.trim()) return;
    onApply(pendingId, note.trim());
    setPendingId(null);
    setNote('');
  };

  if (pending) {
    return (
      <div className="rounded-lg border border-paper-100/12 bg-ink-950 p-4">
        <label className={LABEL} htmlFor="order-action-note">
          {pending.cta}
          {pending.noteRequired ? '' : ' (Optional)'}
        </label>
        <textarea
          id="order-action-note"
          autoFocus
          rows={3}
          className={AREA}
          placeholder={pending.notePrompt}
          value={note}
          onChange={(e) => setNote(e.target.value)}
        />
        <div className="mt-3 flex items-center gap-4">
          <PanelButton
            as="button"
            size="sm"
            variant={pending.variant === 'flare' ? 'flare' : 'outline'}
            onClick={confirmPending}
            disabled={pending.noteRequired && !note.trim()}
            className="pressable disabled:opacity-40"
          >
            {pending.cta}
          </PanelButton>
          <button
            onClick={() => setPendingId(null)}
            className="pressable text-xs text-paper-100/45 transition-colors hover:text-paper-100"
          >
            Cancel
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-wrap items-center gap-3">
      {actionIds.map((id) => {
        const action = ORDER_ACTIONS[id];
        if (action.variant === 'ghost') {
          return (
            <button
              key={id}
              onClick={() => trigger(id)}
              className="pressable ml-auto text-xs text-paper-100/40 transition-colors hover:text-flare"
            >
              {action.cta}
            </button>
          );
        }
        return (
          <PanelButton
            key={id}
            as="button"
            size="sm"
            variant={action.variant}
            className="pressable"
            onClick={() => trigger(id)}
          >
            {action.cta}
          </PanelButton>
        );
      })}
    </div>
  );
}
