// Placeholder marketing content — portfolio, social proof, FAQ, quote engine.
// Front-end only; no real client data.

export const PORTFOLIO = [
  {
    id: 'w1',
    title: 'Custom Suspension Tee',
    client: 'ZYKOTIC Concepts',
    category: 'Apparel',
    year: '2026',
    accent: '#1E7A85',
    image: '/work/zykotic-miami.jpg',
  },
  {
    id: 'w2',
    title: 'Shop Merch Drop',
    client: 'Impressiva Printing',
    category: 'Apparel',
    year: '2026',
    accent: '#e5352b',
    image: '/work/impressiva-merch.jpg',
  },
  {
    id: 'w3',
    title: 'Classic Lineup Tee',
    client: 'Lone Star Muffler & Brake',
    category: 'Apparel',
    year: '2026',
    accent: '#b81f16',
    image: '/work/lone-star-muffler.jpg',
  },
  {
    id: 'w4',
    title: 'OBS Build Tee',
    client: 'LG Autoworks & Customs',
    category: 'Apparel',
    year: '2025',
    accent: '#6b7683',
    image: '/work/lg-autoworks.jpg',
  },
  {
    id: 'w5',
    title: 'Dropped Truck Series',
    client: 'ZYKOTIC Concepts',
    category: 'Apparel',
    year: '2025',
    accent: '#2f6bff',
    image: '/work/zykotic-dropped-trucks.jpg',
  },
  {
    id: 'w6',
    title: 'Hot Rod Flames Graphic',
    client: 'Impressiva Printing',
    category: 'Apparel',
    year: '2025',
    accent: '#e5352b',
    image: '/work/flaming-v8.jpg',
  },
  {
    id: 'w7',
    title: 'Neon District Banners',
    client: 'Riot Coffee',
    category: 'Wide Format',
    year: '2026',
    accent: '#e5352b',
  },
  {
    id: 'w8',
    title: 'Foil Business Suite',
    client: 'Vault Barbers',
    category: 'Business Cards',
    year: '2025',
    accent: '#b81f16',
  },
  {
    id: 'w9',
    title: 'Holographic Sticker Pack',
    client: 'Static Skate',
    category: 'Stickers',
    year: '2025',
    accent: '#6b7683',
  },
];

export const CATEGORIES = ['All', 'Apparel', 'Wide Format', 'Business Cards', 'Stickers'];

export const TESTIMONIALS = [
  {
    quote:
      'They turned a rough concept into a building-side banner in 48 hours, and the color was exactly right.',
    name: 'Marcus Vega',
    role: 'Owner',
    company: 'Riot Coffee',
  },
  {
    quote:
      'Every merchandise run we have ordered has sold out. The print quality is a clear step above anyone we used before.',
    name: 'Dani Okafor',
    role: 'Team Manager',
    company: 'Southside FC',
  },
  {
    quote:
      'The foil business cards draw a comment nearly every time I hand one over. Well worth the investment.',
    name: 'Theo Brandt',
    role: 'Founder',
    company: 'Vault Barbers',
  },
  {
    quote:
      'A rush order on a Friday afternoon, handled without a hitch — proof back within the hour, finished product the next morning.',
    name: 'Priya Nair',
    role: 'Marketing Lead',
    company: 'Golden Wok',
  },
];

export const LOGOS = [
  'RIOT COFFEE',
  'SOUTHSIDE FC',
  'VAULT BARBERS',
  'STATIC SKATE',
  'GOLDEN WOK',
  'EMBER CO.',
  'BASEMENT SHOWS',
  'TAQUERÍA LUZ',
];

export const FAQS = [
  {
    q: 'How fast can you turn a job around?',
    a: 'Standard runs ship in 3–5 business days. Most products offer same-day rush if your files are print-ready and approved before noon.',
  },
  {
    q: 'What files do you need?',
    a: 'Print-ready PDF, PNG, SVG or high-res JPG at 300dpi with a 0.125" bleed. No art? Our designers will build it — just upload a reference from your account.',
  },
  {
    q: 'Do you match exact colors?',
    a: 'Yes. Our presses are G7-calibrated and every job is hand-proofed. For brand-critical work we can hit specified spot/Pantone values.',
  },
  {
    q: 'Is there a minimum order?',
    a: 'Most products start at low quantities — 50 stickers, 100 cards, a single banner. Larger runs unlock better per-unit pricing.',
  },
  {
    q: 'Can I get it shipped?',
    a: 'Shop pickup and local courier are available same-week; we also ship nationwide. Shipping is quoted per job at checkout.',
  },
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
