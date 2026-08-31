import { useRef, useState } from 'react';
import { UploadCloud } from 'lucide-react';
import { ACCEPTED_EXTENSIONS } from '@utils/files.js';

export default function UploadDrop({ onFiles, compact = false }) {
  const inputRef = useRef(null);
  const [dragging, setDragging] = useState(false);

  const handle = (fileList) => {
    if (fileList?.length) onFiles(fileList);
  };

  const openPicker = () => inputRef.current?.click();

  return (
    <div
      role="button"
      tabIndex={0}
      aria-label="Upload Artwork Files"
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          openPicker();
        }
      }}
      onDragOver={(e) => {
        e.preventDefault();
        setDragging(true);
      }}
      onDragLeave={(e) => {
        // Dragging across child elements fires leave events too — only a
        // real exit of the dropzone should drop the highlight.
        if (!e.currentTarget.contains(e.relatedTarget)) setDragging(false);
      }}
      onDrop={(e) => {
        e.preventDefault();
        setDragging(false);
        handle(e.dataTransfer.files);
      }}
      onClick={openPicker}
      className={`pressable flex cursor-pointer flex-col items-center justify-center rounded-lg border border-dashed px-5 text-center transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-flare focus-visible:ring-offset-2 focus-visible:ring-offset-ink-950 ${
        compact ? 'py-4' : 'py-7'
      } ${dragging ? 'border-flare bg-flare/5' : 'border-paper-100/25 hover:border-flare/60'}`}
    >
      <UploadCloud
        className={compact ? 'h-5 w-5 text-flare' : 'h-6 w-6 text-flare'}
        strokeWidth={1.5}
      />
      <p className="mt-3 text-xs font-500 text-paper-100/80">Drop files or click to browse</p>
      <p className="mt-1 text-[11px] text-paper-100/40">PDF, PNG, JPG, WEBP, SVG, GIF · 4MB max</p>
      <input
        ref={inputRef}
        type="file"
        accept={ACCEPTED_EXTENSIONS}
        multiple
        tabIndex={-1}
        aria-hidden
        className="hidden"
        onChange={(e) => {
          handle(e.target.files);
          e.target.value = '';
        }}
      />
    </div>
  );
}
