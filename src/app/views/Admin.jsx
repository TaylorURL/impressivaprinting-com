import { useMemo, useState } from 'react';
import { Download, Layers, Trash2, Users } from 'lucide-react';
import { store, UPLOAD_STATUSES } from '@data/store.js';
import { formatBytes } from '@utils/files.js';
import GlassCard from '@components/GlassCard.jsx';

const STATUS_STYLE = {
  new: 'bg-cyan/15 text-cyan border-cyan/30',
  'in-production': 'bg-gold/15 text-gold border-gold/30',
  ready: 'bg-acid/15 text-acid border-acid/30',
  archived: 'bg-white/10 text-white/50 border-white/20',
};

function AdminTile({ upload, onStatus, onRemove }) {
  return (
    <GlassCard className="overflow-hidden">
      <div className="relative aspect-[4/3] w-full bg-ink-900">
        <img
          src={upload.dataUrl}
          alt={upload.fileName}
          className="h-full w-full object-contain p-3"
        />
        <span
          className={`absolute left-3 top-3 rounded-full border px-2.5 py-1 text-[10px] font-700 uppercase tracking-wide ${
            STATUS_STYLE[upload.status] || STATUS_STYLE.new
          }`}
        >
          {upload.status}
        </span>
      </div>
      <div className="p-4">
        <p className="truncate font-head text-sm font-600 text-white">{upload.fileName}</p>
        <p className="mt-0.5 text-xs text-white/45">
          {upload.userName} · {upload.userEmail}
        </p>
        <div className="mt-1 flex items-center justify-between text-xs text-white/40">
          <span>{upload.product}</span>
          <span>{formatBytes(upload.size)}</span>
        </div>
        {upload.notes ? (
          <p className="mt-2 rounded-lg border border-white/10 bg-white/5 px-3 py-2 text-xs text-white/60">
            {upload.notes}
          </p>
        ) : null}

        <div className="mt-3 flex items-center gap-2">
          <select
            value={upload.status}
            onChange={(e) => onStatus(upload.id, e.target.value)}
            className="flex-1 rounded-lg border border-white/15 bg-ink-800 px-3 py-2 text-xs text-white outline-none transition-colors focus:border-cyan/60"
          >
            {UPLOAD_STATUSES.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
          <a
            href={upload.dataUrl}
            download={upload.fileName}
            className="pressable grid h-8 w-8 place-items-center rounded-lg border border-white/10 text-white/50 hover:border-cyan/60 hover:text-cyan"
            aria-label="Download file"
          >
            <Download className="h-4 w-4" />
          </a>
          <button
            onClick={() => onRemove(upload.id)}
            className="pressable grid h-8 w-8 place-items-center rounded-lg border border-white/10 text-white/50 hover:border-magenta/60 hover:text-magenta"
            aria-label="Delete upload"
          >
            <Trash2 className="h-4 w-4" />
          </button>
        </div>
      </div>
    </GlassCard>
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

  return (
    <div className="mx-auto max-w-6xl px-4 pb-6 sm:px-6">
      <span className="font-graff text-lg text-neon-cyan rotate-[-2deg]">back of house</span>
      <h1 className="mt-1 spray text-5xl text-white sm:text-6xl">
        Admin <span className="clip-text street-gradient">Panel</span>
      </h1>
      <p className="mt-2 text-white/55">Every file customers have dropped, all in one place.</p>

      <div className="mt-8 grid grid-cols-2 gap-4 sm:grid-cols-3">
        <GlassCard className="flex items-center gap-4 p-5">
          <span className="grid h-11 w-11 place-items-center rounded-xl bg-magenta/15 text-neon-magenta">
            <Layers className="h-5 w-5" />
          </span>
          <div>
            <div className="spray text-3xl text-white">{stats.total}</div>
            <div className="text-xs uppercase tracking-widest text-white/45">Total Files</div>
          </div>
        </GlassCard>
        <GlassCard className="flex items-center gap-4 p-5">
          <span className="grid h-11 w-11 place-items-center rounded-xl bg-cyan/15 text-neon-cyan">
            <Users className="h-5 w-5" />
          </span>
          <div>
            <div className="spray text-3xl text-white">{stats.customers}</div>
            <div className="text-xs uppercase tracking-widest text-white/45">Customers</div>
          </div>
        </GlassCard>
        <GlassCard className="col-span-2 flex items-center gap-4 p-5 sm:col-span-1">
          <span className="grid h-11 w-11 place-items-center rounded-xl bg-acid/15 text-neon-acid">
            <Download className="h-5 w-5" />
          </span>
          <div>
            <div className="spray text-3xl text-white">{stats.newCount}</div>
            <div className="text-xs uppercase tracking-widest text-white/45">Awaiting Review</div>
          </div>
        </GlassCard>
      </div>

      <div className="mt-8 flex flex-wrap gap-2">
        {['all', ...UPLOAD_STATUSES].map((s) => (
          <button
            key={s}
            onClick={() => setFilter(s)}
            className={`pressable rounded-full border px-4 py-2 font-head text-xs font-600 uppercase tracking-wide transition-colors ${
              filter === s
                ? 'border-cyan/60 bg-cyan/15 text-white'
                : 'border-white/15 text-white/55 hover:text-white'
            }`}
          >
            {s}
          </button>
        ))}
      </div>

      {visible.length === 0 ? (
        <GlassCard className="mt-8 flex flex-col items-center justify-center px-6 py-20 text-center">
          <span className="grid h-16 w-16 place-items-center rounded-full border border-white/10 bg-white/5">
            <Layers className="h-7 w-7 text-white/40" />
          </span>
          <p className="mt-4 font-head text-lg font-600 text-white">No files in this view</p>
          <p className="mt-1 max-w-xs text-sm text-white/50">
            When customers upload art from their account, it lands right here.
          </p>
        </GlassCard>
      ) : (
        <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
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
    </div>
  );
}
