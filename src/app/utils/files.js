// Print-ready art is usually a PDF, so it sits alongside the image types.
const ACCEPTED_TYPES = [
  'image/png',
  'image/jpeg',
  'image/webp',
  'image/svg+xml',
  'image/gif',
  'application/pdf',
];

export const ACCEPTED_EXTENSIONS = '.png,.jpg,.jpeg,.webp,.svg,.gif,.pdf';

// Files travel to the database as data URLs, so the cap keeps any single
// row — and the upload itself — a sane size.
const MAX_FILE_BYTES = 4 * 1024 * 1024;

export function isImageType(fileType) {
  return String(fileType || '').startsWith('image/');
}

export function formatBytes(bytes) {
  if (!bytes) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  return `${(bytes / Math.pow(1024, i)).toFixed(i === 0 ? 0 : 1)} ${units[i]}`;
}

function readFileAsDataUrl(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = () => reject(new Error('Could not read that file.'));
    reader.readAsDataURL(file);
  });
}

// Shared by every upload surface: validates, reads, and shapes browser File
// objects into the records the store keeps on an order. Invalid files are
// skipped; the last problem message comes back so the UI can surface it.
export async function buildFileRecords(fileList) {
  const records = [];
  let error = null;
  for (const file of Array.from(fileList || [])) {
    const problem = validateFile(file);
    if (problem) {
      error = problem;
      continue;
    }
    try {
      const dataUrl = await readFileAsDataUrl(file);
      records.push({
        fileName: file.name,
        fileType: file.type,
        size: file.size,
        dataUrl,
        uploadedAt: new Date().toISOString(),
      });
    } catch (err) {
      error = err.message;
    }
  }
  return { records, error };
}

function validateFile(file) {
  if (!ACCEPTED_TYPES.includes(file.type)) {
    return 'That file type is not supported. Upload a PDF, PNG, JPG, WEBP, SVG or GIF.';
  }
  if (file.size > MAX_FILE_BYTES) {
    return `That file is too big (${formatBytes(file.size)}). Max is ${formatBytes(MAX_FILE_BYTES)}.`;
  }
  return null;
}
