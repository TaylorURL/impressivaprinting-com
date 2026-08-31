import { CircleDot, MessageSquare, PackagePlus, Paperclip } from 'lucide-react';
import { formatDateTime } from '@utils/format.js';

const KIND_ICON = {
  created: PackagePlus,
  file: Paperclip,
  status: CircleDot,
  note: MessageSquare,
};

// One shared activity feed for both panels; `actorNames` maps the stored
// actor ('customer' | 'shop') to whatever reads right for the viewer.
export default function EventTimeline({ events, actorNames }) {
  const feed = [...events].reverse();
  return (
    <ol>
      {feed.map((event, i) => {
        const Icon = KIND_ICON[event.kind] || CircleDot;
        const isShop = event.actor === 'shop';
        return (
          <li key={event.id} className="relative flex gap-4 pb-6 last:pb-0">
            {i < feed.length - 1 ? (
              <span
                aria-hidden
                className="absolute left-[13px] top-7 h-[calc(100%-16px)] w-px bg-paper-100/10"
              />
            ) : null}
            <span
              className={`spec z-raised grid h-7 w-7 shrink-0 place-items-center rounded-full border bg-ink-900 ${
                isShop ? 'border-flare/50 text-flare' : 'border-paper-100/25 text-paper-100/60'
              }`}
            >
              <Icon className="h-3.5 w-3.5" strokeWidth={1.8} />
            </span>
            <div className="min-w-0 flex-1 pt-1">
              <div className="flex flex-wrap items-baseline justify-between gap-x-3">
                <p className="text-sm text-paper-100/85">{event.label}</p>
                <span className="spec shrink-0 text-[10px] text-paper-100/35">
                  {formatDateTime(event.at)}
                </span>
              </div>
              <p className="mt-1 text-[11px] text-paper-100/45">
                {actorNames[event.actor] || event.actor}
              </p>
              {event.note ? (
                <p className="mt-2 rounded-md border border-paper-100/10 bg-ink-950/60 px-3 py-2 text-xs leading-relaxed text-paper-100/70">
                  {event.note}
                </p>
              ) : null}
            </div>
          </li>
        );
      })}
    </ol>
  );
}
