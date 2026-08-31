import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { FileText, Image as ImageIcon, X } from 'lucide-react';
import { useAuth } from '@hooks/useAuth.js';
import { store } from '@data/store.js';
import { PRODUCTS } from '@constants/products.js';
import { portalOrderPath } from '@constants/routes.js';
import { buildFileRecords, formatBytes, isImageType } from '@utils/files.js';

import PanelPage from '@components/panel/PanelPage.jsx';
import UploadDrop from '@components/panel/UploadDrop.jsx';
import { AREA, FIELD, LABEL, PanelCard, PanelButton } from '@components/panel/ui.jsx';

export default function NewOrder() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({
    productId: PRODUCTS[0].id,
    qty: '',
    size: '',
    finish: '',
    dueDate: '',
    notes: '',
  });
  const [files, setFiles] = useState([]);
  const [error, setError] = useState('');
  const [placing, setPlacing] = useState(false);

  const product = useMemo(
    () => PRODUCTS.find((p) => p.id === form.productId) || PRODUCTS[0],
    [form.productId],
  );
  const update = (key) => (e) => setForm((f) => ({ ...f, [key]: e.target.value }));

  const handleFiles = async (fileList) => {
    setError('');
    const { records, error: problem } = await buildFileRecords(fileList);
    if (problem) setError(problem);
    if (records.length) setFiles((prev) => [...prev, ...records]);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (placing) return;
    setError('');
    const qty = parseInt(form.qty, 10);
    if (!qty || qty < 1) {
      setError('Quantity has to be at least 1.');
      return;
    }
    setPlacing(true);
    try {
      const order = await store.createOrder({
        userId: user.id,
        product: { id: product.id, name: product.name, code: product.code },
        qty,
        size: form.size.trim(),
        finish: form.finish.trim(),
        dueDate: form.dueDate,
        notes: form.notes.trim(),
        files,
      });
      navigate(portalOrderPath(order.id), { replace: true });
    } catch (err) {
      setError(err.message);
      setPlacing(false);
    }
  };

  return (
    <PanelPage context="Orders" title="New Order" meta="Quoted before anything runs">
      <form onSubmit={handleSubmit} className="grid gap-5 lg:grid-cols-[1.4fr_1fr]">
        <PanelCard title="Job Details" className="self-start">
          <div className="space-y-4">
            <div>
              <label className={LABEL} htmlFor="order-product">
                Product
              </label>
              <select
                id="order-product"
                value={form.productId}
                onChange={update('productId')}
                className={`${FIELD} appearance-none`}
              >
                {PRODUCTS.map((p) => (
                  <option key={p.id} value={p.id} className="bg-ink-900 text-paper-100">
                    {p.name}
                  </option>
                ))}
              </select>
              <p className="spec mt-2 text-[10px] text-paper-100/40">
                {product.code} · {product.stock} · {product.details.join(' · ')}
              </p>
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <label className={LABEL} htmlFor="order-qty">
                  Quantity
                </label>
                <input
                  id="order-qty"
                  name="quantity"
                  type="number"
                  inputMode="numeric"
                  autoComplete="off"
                  min="1"
                  placeholder="500"
                  value={form.qty}
                  onChange={update('qty')}
                  className={FIELD}
                  aria-invalid={Boolean(error)}
                  aria-describedby={error ? 'form-error' : undefined}
                  required
                />
              </div>
              <div>
                <label className={LABEL} htmlFor="order-size">
                  Size
                </label>
                <input
                  id="order-size"
                  name="size"
                  type="text"
                  autoComplete="off"
                  placeholder='3.5×2", 6×3ft…'
                  value={form.size}
                  onChange={update('size')}
                  className={FIELD}
                  aria-invalid={Boolean(error)}
                  aria-describedby={error ? 'form-error' : undefined}
                />
              </div>
              <div>
                <label className={LABEL} htmlFor="order-finish">
                  Finish
                </label>
                <input
                  id="order-finish"
                  name="finish"
                  type="text"
                  autoComplete="off"
                  placeholder="Soft-touch, foil, die-cut…"
                  value={form.finish}
                  onChange={update('finish')}
                  className={FIELD}
                  aria-invalid={Boolean(error)}
                  aria-describedby={error ? 'form-error' : undefined}
                />
              </div>
              <div>
                <label className={LABEL} htmlFor="order-due">
                  Need By
                </label>
                <input
                  id="order-due"
                  name="due-date"
                  type="date"
                  autoComplete="off"
                  value={form.dueDate}
                  onChange={update('dueDate')}
                  className={`${FIELD} [color-scheme:dark]`}
                />
              </div>
            </div>

            <div>
              <label className={LABEL} htmlFor="order-notes">
                Notes
              </label>
              <textarea
                id="order-notes"
                rows={3}
                placeholder="Color matching, references, delivery…"
                value={form.notes}
                onChange={update('notes')}
                className={AREA}
              />
            </div>
          </div>
        </PanelCard>

        <div className="space-y-5 self-start">
          <PanelCard title="Artwork" aside={files.length ? `${files.length} added` : 'Optional'}>
            <UploadDrop onFiles={handleFiles} compact />
            {files.length > 0 ? (
              <ul className="mt-3 space-y-2">
                {files.map((file, i) => (
                  <li
                    key={`${file.fileName}-${i}`}
                    className="flex items-center gap-3 border border-paper-100/10 bg-ink-950 px-3 py-2"
                  >
                    {isImageType(file.fileType) ? (
                      <ImageIcon
                        className="h-3.5 w-3.5 shrink-0 text-paper-100/40"
                        strokeWidth={1.8}
                      />
                    ) : (
                      <FileText className="h-3.5 w-3.5 shrink-0 text-flare/70" strokeWidth={1.8} />
                    )}
                    <span className="min-w-0 flex-1 truncate text-xs text-paper-100/80">
                      {file.fileName}
                    </span>
                    <span className="spec shrink-0 text-[10px] text-paper-100/40">
                      {formatBytes(file.size)}
                    </span>
                    <button
                      type="button"
                      onClick={() => setFiles((prev) => prev.filter((_, idx) => idx !== i))}
                      className="pressable shrink-0 text-paper-100/40 hover:text-flare"
                      aria-label={`Remove ${file.fileName}`}
                    >
                      <X className="h-3.5 w-3.5" />
                    </button>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="mt-3 text-xs text-paper-100/45">
                No files yet is fine. The order opens as Awaiting Artwork and files can be added
                later.
              </p>
            )}
          </PanelCard>

          {error ? (
            <p
              id="form-error"
              role="alert"
              className="rounded-md border border-flare/30 bg-flare/10 px-3 py-2 text-xs text-paper-100"
            >
              {error}
            </p>
          ) : null}

          <PanelButton as="button" type="submit" variant="flare" size="md" full disabled={placing}>
            {placing ? 'Placing Order…' : 'Place Order'}
          </PanelButton>
        </div>
      </form>
    </PanelPage>
  );
}
