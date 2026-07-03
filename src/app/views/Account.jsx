import { useCallback, useRef, useState } from 'react';
import { Image as ImageIcon, Trash2, UploadCloud } from 'lucide-react';
import { useAuth } from '@hooks/useAuth.js';
import { store } from '@data/store.js';
import { PRODUCTS } from '@constants/products.js';
import { formatBytes, readFileAsDataUrl, validateFile } from '@utils/files.js';
import GlassCard from '@components/GlassCard.jsx';

const STATUS_STYLE = {
  new: 'bg-cyan/15 text-cyan border-cyan/30',
  'in-production': 'bg-gold/15 text-gold border-gold/30',
  ready: 'bg-acid/15 text-acid border-acid/30',
  archived: 'bg-white/10 text-white/50 border-white/20',
};

function UploadTile({ upload, onRemove }) {
  return (
    <GlassCard className="group overflow-hidden">
      <div className="relative aspect-[4/3] w-full overflow-hidden bg-ink-900">
        <img
          src={upload.dataUrl}
          alt={upload.fileName}
          className="h-full w-full object-contain p-3 transition-transform duration-300 ease-street group-hover:scale-[1.03]"
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
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0">
            <p className="truncate font-head text-sm font-600 text-white">{upload.fileName}</p>
            <p className="mt-0.5 text-xs text-white/45">
              {upload.product} · {formatBytes(upload.size)}
            </p>
          </div>
          <button
            onClick={() => onRemove(upload.id)}
            className="pressable grid h-8 w-8 shrink-0 place-items-center rounded-lg border border-white/10 text-white/50 hover:border-magenta/60 hover:text-magenta"
            aria-label="Delete upload"
          >
            <Trash2 className="h-4 w-4" />
          </button>
        </div>
        {upload.notes ? <p className="mt-2 text-xs text-white/50">{upload.notes}</p> : null}
      </div>
    </GlassCard>
  );
}

export default function Account() {
  const { user } = useAuth();
  const [uploads, setUploads] = useState(() => store.getUploadsForUser(user.id));
  const [product, setProduct] = useState(PRODUCTS[0].name);
  const [notes, setNotes] = useState('');
  const [error, setError] = useState('');
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef(null);

  const refresh = useCallback(() => {
    setUploads(store.getUploadsForUser(user.id));
  }, [user.id]);

  const handleFiles = useCallback(
    async (fileList) => {
      setError('');
      const files = Array.from(fileList || []);
      for (const file of files) {
        const problem = validateFile(file);
        if (problem) {
          setError(problem);
          continue;
        }
        try {
          const dataUrl = await readFileAsDataUrl(file);
          store.addUpload({
            userId: user.id,
            userName: user.name,
            userEmail: user.email,
            fileName: file.name,
            fileType: file.type,
            size: file.size,
            dataUrl,
            product,
            notes,
          });
        } catch (err) {
          setError(err.message);
        }
      }
      setNotes('');
      refresh();
    },
    [user, product, notes, refresh],
  );

  const onDrop = (e) => {
    e.preventDefault();
    setDragging(false);
    handleFiles(e.dataTransfer.files);
  };

  const handleRemove = (id) => {
    store.removeUpload(id);
    refresh();
  };

  return (
    <div className="mx-auto max-w-6xl px-4 pb-6 sm:px-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <span className="font-graff text-lg text-neon-cyan rotate-[-2deg]">your desk</span>
          <h1 className="mt-1 spray text-5xl text-white sm:text-6xl">
            Yo, <span className="clip-text street-gradient">{user.name.split(' ')[0]}</span>
          </h1>
          <p className="mt-2 text-white/55">{user.email}</p>
        </div>
        <div className="rounded-2xl border border-white/10 bg-white/5 px-5 py-3 text-center">
          <div className="spray text-3xl text-white">{uploads.length}</div>
          <div className="text-xs uppercase tracking-widest text-white/45">Files On File</div>
        </div>
      </div>

      <div className="mt-10 grid gap-6 lg:grid-cols-[1fr_1.4fr]">
        {/* Uploader */}
        <GlassCard className="p-7">
          <h2 className="spray text-2xl text-white">Drop Your Art</h2>
          <p className="mt-1 text-sm text-white/55">
            PNG, JPG, WEBP, SVG or GIF. Up to 4MB each. Multiple files welcome.
          </p>

          <div className="mt-5 space-y-4">
            <div>
              <label className="mb-1.5 block text-xs uppercase tracking-widest text-white/45">
                For which product?
              </label>
              <select
                value={product}
                onChange={(e) => setProduct(e.target.value)}
                className="w-full rounded-xl border border-white/15 bg-ink-800 px-4 py-3 text-sm text-white outline-none transition-colors focus:border-cyan/60"
              >
                {PRODUCTS.map((p) => (
                  <option key={p.id} value={p.name}>
                    {p.name}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="mb-1.5 block text-xs uppercase tracking-widest text-white/45">
                Notes (optional)
              </label>
              <input
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="Qty, size, deadline…"
                className="w-full rounded-xl border border-white/15 bg-white/5 px-4 py-3 text-sm text-white placeholder:text-white/35 outline-none transition-colors focus:border-cyan/60"
              />
            </div>
          </div>

          <div
            onDragOver={(e) => {
              e.preventDefault();
              setDragging(true);
            }}
            onDragLeave={() => setDragging(false)}
            onDrop={onDrop}
            onClick={() => inputRef.current?.click()}
            className={`pressable mt-4 flex cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed px-6 py-10 text-center transition-colors ${
              dragging
                ? 'border-cyan/70 bg-cyan/5'
                : 'border-white/15 hover:border-magenta/50 hover:bg-white/[0.03]'
            }`}
          >
            <span className="grid h-14 w-14 place-items-center rounded-2xl street-gradient text-ink-950">
              <UploadCloud className="h-6 w-6" />
            </span>
            <p className="mt-4 font-head text-sm font-600 text-white">
              Drag files here or click to browse
            </p>
            <p className="mt-1 text-xs text-white/45">Your art stays in this browser (demo)</p>
            <input
              ref={inputRef}
              type="file"
              accept="image/*"
              multiple
              className="hidden"
              onChange={(e) => handleFiles(e.target.files)}
            />
          </div>

          {error ? (
            <p className="mt-3 rounded-xl border border-magenta/40 bg-magenta/10 px-4 py-2.5 text-sm text-white">
              {error}
            </p>
          ) : null}
        </GlassCard>

        {/* Gallery */}
        <div>
          <div className="flex items-center justify-between">
            <h2 className="spray text-2xl text-white">Your Uploads</h2>
          </div>

          {uploads.length === 0 ? (
            <GlassCard className="mt-4 flex flex-col items-center justify-center px-6 py-16 text-center">
              <span className="grid h-16 w-16 place-items-center rounded-full border border-white/10 bg-white/5">
                <ImageIcon className="h-7 w-7 text-white/40" />
              </span>
              <p className="mt-4 font-head text-lg font-600 text-white">Nothing here yet</p>
              <p className="mt-1 max-w-xs text-sm text-white/50">
                Drop your first PNG on the left and it&apos;ll show up here — and land on the
                shop&apos;s admin panel.
              </p>
            </GlassCard>
          ) : (
            <div className="mt-4 grid gap-4 sm:grid-cols-2">
              {uploads.map((upload) => (
                <UploadTile key={upload.id} upload={upload} onRemove={handleRemove} />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
