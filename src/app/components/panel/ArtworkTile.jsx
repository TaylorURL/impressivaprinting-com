import { Download, FileText, Trash2 } from 'lucide-react';
import { formatBytes, isImageType } from '@utils/files.js';
import { formatDate } from '@utils/format.js';

// PDFs get a document plate instead of an inline preview, because a PDF data
// URL has nothing an image element can decode. Files the shop attached are
// proofs and get badged as such.
export default function ArtworkTile({ file, onRemove, downloadable = false }) {
  const isProof = file.uploadedBy === 'shop';
  return (
    <div className="group overflow-hidden rounded-lg border border-paper-100/10 bg-ink-900 shadow-card">
      <div className="relative aspect-[4/3] w-full overflow-hidden bg-ink-950">
        <div className="halftone pointer-events-none absolute inset-0 opacity-[0.03]" />
        {isProof ? (
          <span className="spec absolute right-2.5 top-2.5 z-raised rounded bg-flare px-2 py-1 text-[9px] font-700 uppercase tracking-[0.16em] text-white">
            Proof
          </span>
        ) : null}
        {isImageType(file.fileType) ? (
          <img
            src={file.dataUrl}
            alt={`Artwork preview of ${file.fileName}`}
            loading="lazy"
            decoding="async"
            width="800"
            height="600"
            className="relative aspect-[4/3] h-full w-full object-contain p-4 transition-transform duration-500 ease-editorial group-hover:scale-[1.03]"
          />
        ) : (
          <div className="relative flex h-full w-full flex-col items-center justify-center gap-3">
            <FileText className="h-10 w-10 text-flare/70" strokeWidth={1.5} />
            <span className="spec text-[10px] uppercase tracking-[0.2em] text-paper-100/40">
              Print-Ready PDF
            </span>
          </div>
        )}
      </div>
      <div className="border-t border-paper-100/12 p-3">
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0">
            <p className="truncate text-[13px] font-600 text-paper-100">{file.fileName}</p>
            <p className="spec mt-1 text-[10px] text-paper-100/45">
              {formatBytes(file.size)} · {formatDate(file.uploadedAt)}
            </p>
          </div>
          <div className="flex shrink-0 items-center gap-1">
            {downloadable ? (
              <a
                href={file.dataUrl}
                download={file.fileName}
                className="pressable rounded-md p-2 text-paper-100/40 transition-colors hover:bg-paper-100/5 hover:text-flare"
                aria-label={`Download ${file.fileName}`}
                title="Download"
              >
                <Download className="h-4 w-4" />
              </a>
            ) : null}
            {onRemove ? (
              <button
                onClick={() => onRemove(file.id)}
                className="pressable rounded-md p-2 text-paper-100/40 transition-colors hover:bg-paper-100/5 hover:text-flare"
                aria-label={`Remove ${file.fileName}`}
                title="Remove"
              >
                <Trash2 className="h-4 w-4" />
              </button>
            ) : null}
          </div>
        </div>
      </div>
    </div>
  );
}
