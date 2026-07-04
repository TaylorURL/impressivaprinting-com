<p align="center">
  <img src="docs/logo.svg" width="210" alt="Impressiva Printing" />
</p>

<h1 align="center">Impressiva Printing</h1>

<p align="center"><b>A bold custom print-shop site with a street / graffiti, liquid-glass aesthetic.</b></p>
<p align="center">
  Front end for <a href="https://impressivaprinting.com">impressivaprinting.com</a>. <em>Print Loud. Print Proud.</em>
</p>

<p align="center">
  <img alt="React" src="https://img.shields.io/badge/React-19-ff5205?style=for-the-badge&logo=react&logoColor=white" />
  <img alt="Vite" src="https://img.shields.io/badge/Vite-7-ff5205?style=for-the-badge&logo=vite&logoColor=white" />
  <img alt="Tailwind CSS" src="https://img.shields.io/badge/Tailwind_CSS-3-ff5205?style=for-the-badge&logo=tailwindcss&logoColor=white" />
  <img alt="Framer Motion" src="https://img.shields.io/badge/Framer_Motion-11-ff5205?style=for-the-badge&logo=framer&logoColor=white" />
  <img alt="Vercel" src="https://img.shields.io/badge/Vercel-deployed-ff5205?style=for-the-badge&logo=vercel&logoColor=white" />
</p>

<br />

- **Front end only** — no server. Accounts, sessions, and uploaded artwork all live in the browser via `localStorage`.
- **Full storefront** — animated home, filterable product catalog, work portfolio, quote calculator, and a job tracker.
- **Mock accounts** — customers sign up, upload print-ready art, and manage their files; staff review every upload from an admin view.

## Stack

| Layer | Choice |
|-------|--------|
| Framework | React 19 + React Router 7 |
| Build | Vite 7 |
| Styling | Tailwind CSS 3 |
| Motion / icons | Framer Motion · lucide-react |
| Persistence | Browser `localStorage` (no backend) |
| Hosting | Vercel (SPA rewrites in `vercel.json`) |

## Getting started

```bash
npm install
npm run dev        # Vite dev server
npm run build      # production build
npm run lint       # eslint
npm run format     # prettier --write
```

## Pages

| Route | What it is |
|-------|-----------|
| Home | Hero, product marquee, capabilities, process timeline, testimonials, FAQ |
| Products | Full catalog with category filters |
| Work | Portfolio strip of finished jobs |
| About / Contact | Info pages; contact form is demo-only |
| Login / Signup | Mock auth backed by `localStorage` |
| Account | Customers upload PNG/JPG/WEBP/SVG/GIF art (≤ 4 MB) and manage files |
| Admin | Staff view of every uploaded file across customers, with status + delete |

## How persistence works

There is no backend. A single `store.js` module is the whole data layer — it seeds an
admin, tracks the session, and stores uploads as data URLs, all in `localStorage`.

```mermaid
flowchart LR
  U[Visitor] -->|browse| V[React SPA · views]
  V <-->|read / write| S[store.js]
  S --> LS[(localStorage)]
  UP[Upload art] -->|data URL up to 4 MB| S
  ADM[Admin] -->|review / delete| S
```

Because data is per-browser, it clears when the visitor clears site data.

## Demo credentials

An admin is seeded automatically on first load:

```
admin@impressivaprinting.com / admin123
```

Customers create their own accounts via **Sign up**.

## Project structure

```
src/app/
  components/   reusable UI (Nav, Marquee, QuoteCalculator, JobTracker, …)
  views/        pages (Home, Products, Work, Account, Admin, …)
  context/      auth context + provider
  data/store.js localStorage persistence layer
  constants/    site config, product catalog, routes
  utils/        upload validation (type + 4 MB cap)
public/         favicon, release.json
```

## License

Private project — all rights reserved. Made by [TaylorURL](https://taylorurl.com).
