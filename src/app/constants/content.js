// Placeholder marketing content — portfolio and instant-quote engine.
// Front-end only; no real client data.

export const PORTFOLIO = [
  {
    id: 'w1',
    title: 'Neon District Banners',
    client: 'Riot Coffee',
    category: 'Wide Format',
    year: '2026',
    accent: '#e5352b',
    kind: 'banner',
  },
  {
    id: 'w2',
    title: 'Team Apparel Drop',
    client: 'Southside FC',
    category: 'Apparel',
    year: '2026',
    accent: '#2f6bff',
    kind: 'apparel',
  },
  {
    id: 'w3',
    title: 'Foil Business Suite',
    client: 'Vault Barbers',
    category: 'Business Cards',
    year: '2025',
    accent: '#b81f16',
    kind: 'cards',
  },
  {
    id: 'w4',
    title: 'Holographic Sticker Pack',
    client: 'Static Skate',
    category: 'Stickers',
    year: '2025',
    accent: '#6b7683',
    kind: 'sticker',
  },
  {
    id: 'w5',
    title: 'Storefront Signage',
    client: 'Golden Wok',
    category: 'Signage',
    year: '2025',
    accent: '#e5352b',
    kind: 'sign',
  },
  {
    id: 'w6',
    title: 'Gig Poster Series',
    client: 'Basement Shows',
    category: 'Posters',
    year: '2024',
    accent: '#2f6bff',
    kind: 'poster',
  },
  {
    id: 'w7',
    title: 'Bespoke Mailer Boxes',
    client: 'Ember Candle Co.',
    category: 'Packaging',
    year: '2024',
    accent: '#b81f16',
    kind: 'box',
  },
  {
    id: 'w8',
    title: 'Laminated Menu System',
    client: 'Taquería Luz',
    category: 'Menus',
    year: '2024',
    accent: '#6b7683',
    kind: 'menu',
  },
];

export const CATEGORIES = [
  'All',
  'Wide Format',
  'Apparel',
  'Business Cards',
  'Stickers',
  'Signage',
  'Posters',
];

// Instant-quote engine (placeholder math — indicative only, not a real cart).
export const QUOTE_PRODUCTS = [
  { id: 'cards', name: 'Business Cards', base: 0.28, unit: 'card' },
  { id: 'banners', name: 'Vinyl Banners', base: 42, unit: 'banner' },
  { id: 'apparel', name: 'Custom Apparel', base: 16, unit: 'piece' },
  { id: 'stickers', name: 'Stickers', base: 0.42, unit: 'sticker' },
  { id: 'flyers', name: 'Flyers', base: 0.14, unit: 'flyer' },
];

export const QUOTE_QUANTITIES = [50, 100, 250, 500, 1000];

export const QUOTE_FINISHES = [
  { id: 'standard', name: 'Standard', mult: 1 },
  { id: 'matte', name: 'Soft-Touch Matte', mult: 1.25 },
  { id: 'foil', name: 'Foil / Spot UV', mult: 1.6 },
];

export const QUOTE_TURNAROUND = [
  { id: 'standard', name: 'Standard · 3–5 days', mult: 1 },
  { id: 'rush', name: 'Rush · Same day', mult: 1.4 },
];

export const TIMELINE = [
  {
    year: '2019',
    title: 'One Press, One Room',
    body: 'Founded in a single warehouse room, printing event posters and custom apparel for local businesses.',
  },
  {
    year: '2021',
    title: 'Expanding the Floor',
    body: 'Added wide-format and DTF capabilities. Our first storefront banners went up across the district.',
  },
  {
    year: '2023',
    title: 'G7 Calibrated',
    body: 'Implemented shop-wide G7 color management. Hand-proofing became standard on every order.',
  },
  {
    year: '2025',
    title: 'Full Production Floor',
    body: 'A complete production floor — offset, digital, screen, embroidery, and wide-format under one roof.',
  },
  {
    year: '2026',
    title: 'Nationwide Reach',
    body: 'Nationwide shipping, same-day rush service, and more than 18,000 jobs completed.',
  },
];
