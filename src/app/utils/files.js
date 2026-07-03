export const ACCEPTED_TYPES = [
  'image/png',
  'image/jpeg',
  'image/webp',
  'image/svg+xml',
  'image/gif',
];

// localStorage is small; cap individual files so the demo store doesn't overflow.
export const MAX_FILE_BYTES = 4 * 1024 * 1024; // 4MB

export function formatBytes(bytes) {
  if (!bytes) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  return `${(bytes / Math.pow(1024, i)).toFixed(i === 0 ? 0 : 1)} ${units[i]}`;
}

export function readFileAsDataUrl(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = () => reject(new Error('Could not read that file.'));
    reader.readAsDataURL(file);
  });
}

export function validateFile(file) {
  if (!ACCEPTED_TYPES.includes(file.type)) {
    return 'That file type is not supported. Upload a PNG, JPG, WEBP, SVG or GIF.';
  }
  if (file.size > MAX_FILE_BYTES) {
    return `That file is too big (${formatBytes(file.size)}). Max is ${formatBytes(MAX_FILE_BYTES)}.`;
  }
  return null;
}
