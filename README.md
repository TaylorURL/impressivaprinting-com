<img src="public/logo.png" width="260" alt="Impressiva Printing" />

# Impressiva Printing

Website and customer portal for Impressiva Printing, a print shop in Pasadena.

[impressivaprinting.com](https://www.impressivaprinting.com)

<img src="https://img.shields.io/badge/version-2026.44.1-e5352b?style=for-the-badge" alt="Version 2026.44.1" />

The public side is the catalog and a filterable portfolio. Behind sign-in, customers start jobs, upload artwork, approve proofs and track orders. Staff run the same orders from an admin dashboard with a review queue, proofs, a customer list and internal notes.

## How it's built

- **Postgres does the access control.** Accounts, orders, files and the activity timeline sit behind row level security. Staff see everything. Customers see their own. The React app talks to Supabase directly. No app server.
- **Order status is enforced in the database.** Every order runs awaiting artwork, artwork review, proof approval, in production, ready, completed. Triggers on `orders` limit customers to their own moves (submit art, pull it back, cancel while waiting on art, approve or reject a proof). Anything else raises "That status change is the shop's to make."
- **Status changes are compare-and-set.** The app updates against the status the caller saw, so a button rendered from a stale view refuses instead of overwriting.
- **Files are data URLs in Postgres.** Artwork and proofs go in `order_files`, capped at 4 MB in the app. List queries skip the data column. Only the order detail view pulls it.
- **Admins come from a table.** An email listed in `admin_emails` gets the admin role when it signs up, set by the signup trigger.
- **Removing a customer is one call.** `admin_remove_customer` deletes the auth account, profile, orders and files server-side, and refuses staff targets.

<details>
<summary>Decisions and tradeoffs</summary>

- `scripts/critical-css.js` inlines the rules the first screen needs with Beasties. The full sheet loads without holding the paint.
- `scripts/paint-first.js` swaps the entry script for a small inline module that loads the bundle after the first frame. A hidden tab boots right away, since it never paints a frame to wait for.
- Uploads accept PDF, PNG, JPEG, WEBP, SVG and GIF.
- `middleware.js` checks a TaylorURL status endpoint and shows a holding page if the site is paused. Fails open. `api/version.js` returns the deployed commit, uncached.

</details>

<details>
<summary>Running it locally</summary>

You need Node 22 or newer.

```bash
npm install
npm run dev        # Vite dev server
npm run build      # production build to dist/
npm test           # Node test runner
```

There's nothing to configure. The Supabase URL and publishable key are already in the build. To point it at a different Supabase project, copy `.env.example` to `.env` and set `VITE_SUPABASE_URL` and `VITE_SUPABASE_PUBLISHABLE_KEY`.

Staff accounts come from the `admin_emails` table. An email listed there becomes an admin when it signs up.

</details>

## Built with

React 19, React Router, Vite, Tailwind CSS and Supabase (Auth and Postgres). Hosted on Vercel.

<details>
<summary>License</summary>

Proprietary. Copyright (c) 2026 TaylorURL LLC, all rights reserved. See [LICENSE.md](LICENSE.md).

</details>

Built and maintained by [TaylorURL](https://www.taylorurl.com).
