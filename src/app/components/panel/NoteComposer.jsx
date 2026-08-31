import { useState } from 'react';
import { Send } from 'lucide-react';
import { AREA } from '@components/panel/ui.jsx';

export default function NoteComposer({ onSend, placeholder }) {
  const [note, setNote] = useState('');

  const submit = (e) => {
    e.preventDefault();
    const text = note.trim();
    if (!text) return;
    onSend(text);
    setNote('');
  };

  return (
    <form onSubmit={submit} className="mt-4 border-t border-paper-100/8 pt-4">
      <label className="sr-only" htmlFor="order-note">
        Note on This Order
      </label>
      <textarea
        id="order-note"
        rows={2}
        className={AREA}
        placeholder={placeholder || 'Leave a note on this order…'}
        value={note}
        onChange={(e) => setNote(e.target.value)}
      />
      <button
        type="submit"
        disabled={!note.trim()}
        className="pressable mt-2 inline-flex items-center gap-2 rounded-md border border-paper-100/15 bg-ink-850 px-3 py-2 text-xs font-600 text-paper-100/80 transition-colors hover:border-paper-100/30 hover:text-paper-100 disabled:pointer-events-none disabled:opacity-40"
      >
        <Send className="h-3.5 w-3.5" /> Send Note
      </button>
    </form>
  );
}
