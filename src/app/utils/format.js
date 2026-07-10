// Two-digit zero-padded string for editorial index numbers ("01", "02", …).
export function pad2(value) {
  return String(value).padStart(2, '0');
}
