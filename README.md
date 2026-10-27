<p align="center">
  <img src="public/logo.png" width="260" alt="Impressiva Printing" />
</p>

<h1 align="center">Impressiva Printing</h1>

<p align="center">Website and customer portal for Impressiva Printing, a print shop in Pasadena.</p>
<p align="center"><a href="https://www.impressivaprinting.com">impressivaprinting.com</a></p>

<p align="center">
  <img src="https://img.shields.io/badge/version-2026.43.1-e5352b?style=for-the-badge" alt="Version 2026.43.1" />
</p>

Impressiva Printing is a custom print shop in Pasadena that does business cards, vinyl banners, apparel, stickers and signage. The public site shows the catalog and recent work. Behind a sign-in, customers start jobs, upload artwork, approve proofs and track their orders, and staff run the same jobs from an admin dashboard.

## What's on the site

- A product catalog with the specs for each item, and a portfolio of recent work you can filter by category.
- Customer accounts with sign-up, login and password reset.
- A client portal to start a job, upload print-ready artwork (PDF, PNG, JPEG, WEBP, SVG or GIF, up to 4 MB), approve a proof or ask for changes, and see each order's history.
- An admin dashboard with a review queue, artwork review, proofs, a customer list and internal notes on each customer.
- Every order moves through the same steps on both sides: awaiting artwork, artwork review, proof approval, in production, ready, completed.

## Running it locally

You need Node 22 or newer.

```bash
npm install
npm run dev        # Vite dev server
npm run build      # production build to dist/
npm test           # Node test runner
```

There's nothing to configure. The Supabase URL and publishable key are already in the build. To point it at a different Supabase project, copy `.env.example` to `.env` and set `VITE_SUPABASE_URL` and `VITE_SUPABASE_PUBLISHABLE_KEY`.

Staff accounts come from the `admin_emails` table. An email listed there becomes an admin when it signs up.

## Built with

React 19, React Router, Vite, Tailwind CSS and Supabase (Auth and Postgres). Hosted on Vercel.

## License

Proprietary. Copyright (c) 2026 TaylorURL LLC, all rights reserved. See [LICENSE.md](LICENSE.md).

Built and maintained by [TaylorURL](https://www.taylorurl.com).
