// The shop's zone. A stamp on an order is an instant, and the hour a person
// reads off it belongs to the counter the order was taken at rather than to
// whichever browser opened the panel.
const ZONE = 'America/Chicago';

const DATE_ONLY = /^(\d{4})-(\d{2})-(\d{2})$/;

// Fixed en-US locale so the mono spec type lines up the same for everyone.
//
// A date-only value is a square on a calendar rather than a moment: a due date
// somebody picked is the 5th wherever it is read. It is held at UTC midnight
// and written back out of UTC so it prints the square it came from, while a
// full timestamp is written in the shop's zone.
export function formatDate(value) {
  if (!value) return '-';
  const dateOnly = DATE_ONLY.exec(value);
  if (dateOnly) {
    return new Date(`${value}T00:00:00Z`).toLocaleDateString('en-US', {
      timeZone: 'UTC',
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  }
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return '-';
  return d.toLocaleDateString('en-US', {
    timeZone: ZONE,
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
}

export function formatDateTime(iso) {
  if (!iso) return '-';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '-';
  const date = d.toLocaleDateString('en-US', { timeZone: ZONE, month: 'short', day: 'numeric' });
  const time = d.toLocaleTimeString('en-US', {
    timeZone: ZONE,
    hour: 'numeric',
    minute: '2-digit',
  });
  return `${date} · ${time}`;
}

/** The year here, for a line that names the shop rather than the reader. */
export function currentYear() {
  return Number(
    new Intl.DateTimeFormat('en-CA', { timeZone: ZONE, year: 'numeric' }).format(new Date()),
  );
}

export function initials(name) {
  return String(name || '')
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0].toUpperCase())
    .join('');
}

export function plural(count, singular, pluralForm) {
  return count === 1 ? singular : pluralForm || `${singular}s`;
}
