import { useMemo, useState } from 'react';
import { Download, Trash2 } from 'lucide-react';
import { store, UPLOAD_STATUSES } from '@data/store.js';
import { formatBytes } from '@utils/files.js';
import { CONTAINER, UPLOAD_STATUS_STYLE } from '@constants/ui.js';
import CountUp from '@components/CountUp.jsx';
import { ColorBar } from '@components/PrintMarks.jsx';
import { SplitText, LetterGlitch } from '@reactbits';

function AdminTile({ upload, onStatus, onRemove }) {
  return (
    <div className="border border-paper-100/12 bg-ink-900">
      <div className="relative aspect-[4/3] w-full bg-ink-950">
        <div className="halftone pointer-events-none absolute inset-0 opacity-[0.03]" />
        <img
          src={upload.dataUrl}
          alt={upload.fileName}
          className="relative h-full w-full object-contain p-4"
        />
        <span
          className={`spec absolute left-3 top-3 text-[10px] uppercase tracking-[0.2em] ${UPLOAD_STATUS_STYLE[upload.status]}`}
        >
          <span className="mr-1.5 inline-block h-1.5 w-1.5 rounded-full bg-current align-middle" />
          {upload.status}
        </span>
      </div>
      <div className="border-t border-paper-100/12 p-4">
        <p className="truncate font-head text-sm font-700 text-paper-100">{upload.fileName}</p>
        <p className="spec mt-1 text-[11px] text-paper-100/45">
          {upload.userName} · {upload.userEmail}
        </p>
        <div className="spec mt-1 flex items-center justify-between text-[11px] text-paper-100/40">
          <span>{upload.product}</span>
          <span>{formatBytes(upload.size)}</span>
        </div>
        {upload.notes ? (
          <p className="mt-2 border-l border-flare/60 pl-3 text-xs text-paper-100/55">
            {upload.notes}
          </p>
        ) : null}

        <div className="mt-4 flex items-center gap-2">
          <select
            value={upload.status}
            onChange={(e) => onStatus(upload.id, e.target.value)}
            className="spec flex-1 border border-paper-100/15 bg-ink-950 px-3 py-2 text-[11px] uppercase tracking-[0.12em] text-paper-100 outline-none transition-colors focus:border-flare"
          >
            {UPLOAD_STATUSES.map((s) => (
              <option key={s} value={s} className="bg-ink-900">
                {s}
              </option>
            ))}
          </select>
          <a
            href={upload.dataUrl}
            download={upload.fileName}
            className="pressable border border-paper-100/15 p-2 text-paper-100/50 hover:border-flare hover:text-flare"
            aria-label="Download file"
          >
            <Download className="h-4 w-4" />
          </a>
          <button
            onClick={() => onRemove(upload.id)}
            className="pressable border border-paper-100/15 p-2 text-paper-100/50 hover:border-flare hover:text-flare"
            aria-label="Delete upload"
          >
            <Trash2 className="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>
  );
}

export default function Admin() {
  const [uploads, setUploads] = useState(() => store.getUploads());
  const [filter, setFilter] = useState('all');

  const refresh = () => setUploads(store.getUploads());
  const handleStatus = (id, status) => {
    store.setUploadStatus(id, status);
    refresh();
  };
  const handleRemove = (id) => {
    store.removeUpload(id);
    refresh();
  };

  const stats = useMemo(() => {
    const customers = new Set(uploads.map((u) => u.userEmail));
    return {
      total: uploads.length,
      customers: customers.size,
      newCount: uploads.filter((u) => u.status === 'new').length,
    };
  }, [uploads]);

  const visible = filter === 'all' ? uploads : uploads.filter((u) => u.status === filter);
  const STAT_ROWS = [
    { v: stats.total, k: 'Total Files' },
    { v: stats.customers, k: 'Customers' },
    { v: stats.newCount, k: 'Awaiting Review' },
  ];

  return (
    <>
      <section className="cropmarks relative overflow-hidden border-b border-paper-100/10 text-paper-100/40">
        {/* react-bits LetterGlitch — back-of-house terminal backdrop */}
        <div className="pointer-events-none absolute inset-0 opacity-[0.16]">
          <LetterGlitch glitchSpeed={65} fontSize={16} />
        </div>
        <div className={`relative ${CONTAINER} pb-10 pt-14 sm:pt-20`}>
          <div className="flex items-center justify-between border-b border-paper-100/12 pb-4">
            <span className="kicker text-flare">Back of House</span>
            <span className="kicker text-paper-100/50">Restricted</span>
          </div>
          <h1 className="display mt-8 text-[15vw] leading-[0.8] text-paper-100 sm:text-8xl">
            <SplitText text="Admin " splitType="chars" delay={28} />
            <span className="text-flare">
              <SplitText text="Panel" splitType="chars" delay={28} />
            </span>
          </h1>
          <p className="mt-4 text-paper-100/55">
            Every file customers have dropped, all in one place.
          </p>
        </div>
        <ColorBar className="h-2" />
      </section>

      <section className={`${CONTAINER} py-14`}>
        <div className="grid grid-cols-1 border border-paper-100/12 sm:grid-cols-3">
          {STAT_ROWS.map((s, i) => (
            <div
              key={s.k}
              className={`p-6 ${i !== 0 ? 'border-t border-paper-100/12 sm:border-l sm:border-t-0' : ''}`}
            >
              <CountUp value={String(s.v)} className="display block text-5xl text-paper-100" />
              <div className="kicker mt-2 text-paper-100/45">{s.k}</div>
            </div>
          ))}
        </div>

        <div className="mt-8 flex flex-wrap gap-5">
          {['all', ...UPLOAD_STATUSES].map((s) => (
            <button
              key={s}
              onClick={() => setFilter(s)}
              className={`spec pressable pb-1 text-xs uppercase tracking-[0.18em] transition-colors ${
                filter === s
                  ? 'border-b border-flare text-flare'
                  : 'text-paper-100/50 hover:text-paper-100'
              }`}
            >
              {s}
            </button>
          ))}
        </div>

        {visible.length === 0 ? (
          <div className="mt-10 flex flex-col items-center justify-center border border-dashed border-paper-100/15 px-6 py-24 text-center">
            <span className="display text-6xl text-paper-100/15">00</span>
            <p className="spec mt-4 text-xs uppercase tracking-[0.15em] text-paper-100/60">
              No files in this view
            </p>
            <p className="mt-2 max-w-xs text-sm text-paper-100/45">
              When customers upload art from their account, it lands right here.
            </p>
          </div>
        ) : (
          <div className="mt-8 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
            {visible.map((upload) => (
              <AdminTile
                key={upload.id}
                upload={upload}
                onStatus={handleStatus}
                onRemove={handleRemove}
              />
            ))}
          </div>
        )}
      </section>
    </>
  );
}
