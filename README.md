<img src="public/logo.png" width="260" alt="Impressiva Printing" />

# Impressiva Printing

Website and customer portal for Impressiva Printing, a print shop in Pasadena.

[impressivaprinting.com](https://www.impressivaprinting.com)

<img src="https://img.shields.io/badge/version-2026.44.1-e5352b?style=for-the-badge" alt="Version 2026.44.1" />

The public side is the catalog and a filterable portfolio. Behind sign-in, customers start jobs, upload artwork, approve proofs and track orders. Staff run the same orders from an admin dashboard with a review queue, proofs, a customer list and internal notes.

There's no app server. The React app talks to Supabase directly, and Postgres decides who sees what: row level security covers accounts, orders, files and the activity timeline, with staff seeing everything and customers seeing their own.

## Order status lives in the database

An order moves through awaiting artwork, artwork review, proof approval, in production, ready and completed. Triggers on `orders` only let a customer make their own moves: submit art, pull it back, cancel while waiting on art, approve or reject a proof. Anything else raises "That status change is the shop's to make."

Updates are compare-and-set against the status the caller last saw. A button rendered from a stale page refuses instead of overwriting what staff just did.

## Smaller things

- Artwork and proofs are stored as data URLs in `order_files`, capped at 4 MB in the app. List queries skip that column and only the order detail view loads it. PDF, PNG, JPEG, WEBP, SVG and GIF are accepted.
- Staff are whoever is listed in `admin_emails`. The signup trigger gives them the admin role.
- `admin_remove_customer` deletes the auth account, profile, orders and files in one call, and won't touch staff.
- `scripts/critical-css.js` inlines the first screen's CSS with Beasties, and `scripts/paint-first.js` waits for the first frame before loading the bundle. Hidden tabs never paint, so they boot right away.

```bash
npm install
npm run dev
npm run build
npm test
```

Node 22 or newer. The Supabase URL and publishable key are already in the build. To use another project, set `VITE_SUPABASE_URL` and `VITE_SUPABASE_PUBLISHABLE_KEY` in `.env`.

React 19, React Router, Vite, Tailwind CSS and Supabase, on Vercel. Proprietary, see [LICENSE.md](LICENSE.md).

Built and maintained by [TaylorURL](https://www.taylorurl.com).
