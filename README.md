# Impressiva Printing

Front-end for **impressivaprinting.com** — a custom print shop with a GTA / street / graffiti / liquid-glass aesthetic and a modern twist.

Built with **React 19 + Vite + Tailwind CSS**. This is a **front-end-only** build: there is no server. Accounts, sessions, and uploaded artwork all persist in the browser via `localStorage`.

## Stack

- React 19, React Router 7
- Vite 7
- Tailwind CSS 3
- Framer Motion, lucide-react

## What's in it

- **Home** — hero, product marquee, featured products, process, CTA
- **Products** — full catalog with filters
- **About** / **Contact** — informational pages (contact form is demo-only)
- **Login / Signup** — mock auth backed by `localStorage`
- **Account** — customers upload PNG/JPG/WEBP/SVG/GIF art and manage their files
- **Admin** — staff view of every uploaded file across all customers, with status + delete

## Demo credentials

Admin account is seeded automatically:

```
admin@impressivaprinting.com / admin123
```

Customers create their own accounts via **Sign up**.

## Develop

```bash
npm install
npm run dev
npm run build
npm run lint
npm run format
```

## Notes

- Uploads are stored as data URLs in `localStorage`, capped at 4MB each for demo stability.
- Because there is no backend, data is per-browser and clears when site data is cleared.
- Deployed on Vercel; `vercel.json` rewrites all routes to `index.html` for the SPA.
