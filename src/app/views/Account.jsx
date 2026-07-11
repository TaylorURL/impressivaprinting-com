import { useCallback, useRef, useState } from 'react';
import { Trash2, UploadCloud } from 'lucide-react';
import { useAuth } from '@hooks/useAuth.js';
import { store } from '@data/store.js';
import { PRODUCTS } from '@constants/products.js';
import { formatBytes, readFileAsDataUrl, validateFile } from '@utils/files.js';
import Reveal from '@components/Reveal.jsx';
import JobTracker from '@components/JobTracker.jsx';
import { ColorBar } from '@components/PrintMarks.jsx';
import { SplitText, DecryptedText, Squares } from '@reactbits';

const WRAP = 'mx-auto max-w-[1400px] px-5 sm:px-8';
const LABEL = 'kicker mb-2 block text-paper-100/45';
const FIELD =
  'w-full border-b border-paper-100/20 bg-transparent py-2.5 text-sm text-paper-100 placeholder:text-paper-100/30 outline-none transition-colors focus:border-flare';

const STATUS_STYLE = {
  new: 'text-proc-c',
  'in-production': 'text-proc-y',
  ready: 'text-flare',
  archived: 'text-paper-100/40',
};

function UploadTile({ upload, onRemove }) {
  return (
    <div className="group border border-paper-100/12 bg-ink-900">
      <div className="relative aspect-[4/3] w-full overflow-hidden bg-ink-950">
        <div className="halftone pointer-events-none absolute inset-0 opacity-[0.03]" />
        <img
          src={upload.dataUrl}
          alt={upload.fileName}
          className="relative h-full w-full object-contain p-4 transition-transform duration-500 ease-editorial group-hover:scale-[1.03]"
        />
        <span
          className={`spec absolute left-3 top-3 text-[10px] uppercase tracking-[0.2em] ${STATUS_STYLE[upload.status]}`}
        >
          <span className="mr-1.5 inline-block h-1.5 w-1.5 rounded-full bg-current align-middle" />
          {upload.status}
        </span>
      </div>
      <div className="border-t border-paper-100/12 p-4">
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0">
            <p className="truncate font-head text-sm font-700 text-paper-100">{upload.fileName}</p>
            <p className="spec mt-1 text-[11px] text-paper-100/45">
              {upload.product} · {formatBytes(upload.size)}
            </p>
          </div>
          <button
            onClick={() => onRemove(upload.id)}
            className="pressable shrink-0 text-paper-100/40 hover:text-flare"
            aria-label="Delete upload"
          >
            <Trash2 className="h-4 w-4" />
          </button>
        </div>
        {upload.notes ? <p className="mt-2 text-xs text-paper-100/50">{upload.notes}</p> : null}
      </div>
    </div>
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

  const refresh = useCallback(() => setUploads(store.getUploadsForUser(user.id)), [user.id]);

  const handleFiles = useCallback(
    async (fileList) => {
      setError('');
      for (const file of Array.from(fileList || [])) {
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
    <>
      <section className="cropmarks relative overflow-hidden border-b border-paper-100/10 text-paper-100/40">
        {/* react-bits Squares — drifting grid behind the client dashboard header */}
        <div className="pointer-events-none absolute inset-0 opacity-40">
          <Squares direction="diagonal" speed={0.22} squareSize={48} />
        </div>
        <div className={`relative ${WRAP} pb-10 pt-14 sm:pt-20`}>
          <div className="flex items-center justify-between border-b border-paper-100/12 pb-4">
            <span className="kicker text-paper-100/50">Client Dashboard</span>
            <span className="spec text-xs text-paper-100/50">{uploads.length} FILES ON FILE</span>
          </div>
          <h1 className="display mt-8 text-[15vw] leading-[0.8] text-paper-100 sm:text-8xl">
            <SplitText text="Welcome, " splitType="chars" delay={26} />
            <span className="text-flare">
              <SplitText text={user.name.split(' ')[0]} splitType="chars" delay={26} />
            </span>
          </h1>
          <DecryptedText
            text={user.email}
            className="spec mt-4 block text-xs text-paper-100/50"
            encryptedClassName="text-flare/70"
            speed={26}
          />
        </div>
        <ColorBar className="h-2" />
      </section>

      <section className={`${WRAP} grid gap-8 py-14 lg:grid-cols-[0.9fr_1.4fr]`}>
        {/* Uploader */}
        <div className="self-start border border-paper-100/12 p-7">
          <span className="kicker text-flare">Upload</span>
          <h2 className="display mt-3 text-3xl text-paper-100">Upload Artwork</h2>
          <p className="mt-2 text-sm text-paper-100/55">
            PNG, JPG, WEBP, SVG or GIF · up to 4MB each.
          </p>

          <div className="mt-6 space-y-5">
            <div>
              <label className={LABEL}>For which product</label>
              <select
                value={product}
                onChange={(e) => setProduct(e.target.value)}
                className={`${FIELD} appearance-none`}
              >
                {PRODUCTS.map((p) => (
                  <option key={p.id} value={p.name} className="bg-ink-900 text-paper-100">
                    {p.name}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className={LABEL}>Notes (optional)</label>
              <input
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="Qty, size, deadline…"
                className={FIELD}
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
            className={`pressable mt-6 flex cursor-pointer flex-col items-center justify-center border border-dashed px-6 py-10 text-center transition-colors ${
              dragging ? 'border-flare bg-flare/5' : 'border-paper-100/25 hover:border-flare/60'
            }`}
          >
            <UploadCloud className="h-7 w-7 text-flare" strokeWidth={1.6} />
            <p className="spec mt-4 text-xs uppercase tracking-[0.15em] text-paper-100">
              Drag files or click to browse
            </p>
            <p className="spec mt-1 text-[11px] text-paper-100/40">Stored in this browser (demo)</p>
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
            <p className="spec mt-4 border-l-2 border-flare bg-flare/10 px-4 py-2.5 text-xs text-paper-100">
              {error}
            </p>
          ) : null}
        </div>

        {/* Gallery */}
        <div>
          <div className="flex items-center justify-between border-b border-paper-100/12 pb-3">
            <span className="kicker text-paper-100/50">Your Uploads</span>
            <span className="spec text-xs text-paper-100/40">
              {String(uploads.length).padStart(2, '0')}
            </span>
          </div>

          {uploads.length === 0 ? (
            <div className="mt-8 flex flex-col items-center justify-center border border-dashed border-paper-100/15 px-6 py-20 text-center">
              <span className="display text-6xl text-paper-100/15">00</span>
              <p className="spec mt-4 text-xs uppercase tracking-[0.15em] text-paper-100/60">
                Nothing here yet
              </p>
              <p className="mt-2 max-w-xs text-sm text-paper-100/45">
                Drop your first file on the left — it shows here and lands on the shop&apos;s admin
                panel.
              </p>
            </div>
          ) : (
            <div className="mt-6 grid gap-5 sm:grid-cols-2">
              {uploads.map((upload, i) => (
                <Reveal key={upload.id} delay={i * 50}>
                  <UploadTile upload={upload} onRemove={handleRemove} />
                </Reveal>
              ))}
            </div>
          )}
        </div>
      </section>

      <section className={`${WRAP} pb-16`}>
        <JobTracker />
      </section>
    </>
  );
}
