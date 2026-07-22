<p align="center">
  <img src="public/logo.png" width="320" alt="Impressiva Printing" />
</p>

<h1 align="center">Impressiva Printing</h1>

<p align="center">
  <b>A bold custom print-shop storefront with a street / graffiti, liquid-glass aesthetic.</b>
</p>
<p align="center">
  The front end for <a href="https://impressivaprinting.com">impressivaprinting.com</a> — an animated<br />
  React catalog, quote calculator, and mock account system, with no backend to run.
</p>

<p align="center">
  <img alt="React" src="https://img.shields.io/badge/React-19-2563eb?style=for-the-badge&logo=react&logoColor=white" />
  <img alt="Vite" src="https://img.shields.io/badge/Vite-7-2563eb?style=for-the-badge&logo=vite&logoColor=white" />
  <img alt="Tailwind CSS" src="https://img.shields.io/badge/Tailwind_CSS-3-2563eb?style=for-the-badge&logo=tailwindcss&logoColor=white" />
  <img alt="Framer Motion" src="https://img.shields.io/badge/Framer_Motion-11-1f56cf?style=for-the-badge&logo=framer&logoColor=white" />
  <img alt="Vercel" src="https://img.shields.io/badge/Vercel-deployed-3b82f6?style=for-the-badge&logo=vercel&logoColor=white" />
  <img alt="License" src="https://img.shields.io/badge/license-private-2563eb?style=for-the-badge" />
</p>

<br />

## Why Impressiva Printing

A print shop needs a storefront that looks as loud as its work — but not every marketing site needs a server behind it. Impressiva is a fully interactive single-page app that ships as static files: customers browse the catalog, request a quote, sign up, and upload print-ready art, while staff review every file from an admin view. Everything runs in the browser via `localStorage`, so there is nothing to host but the build.

<table width="100%">
  <tr>
    <td width="33%" valign="top">
      <h3 align="center">Front end only</h3>
      <p align="center">No server. Accounts, sessions, and uploaded artwork all live in the browser through a single <code>store.js</code> data layer.</p>
    </td>
    <td width="33%" valign="top">
      <h3 align="center">Full storefront</h3>
      <p align="center">Animated home, filterable product catalog, work portfolio, quote calculator, and a job tracker — one cohesive React SPA.</p>
    </td>
    <td width="33%" valign="top">
      <h3 align="center">Mock accounts</h3>
      <p align="center">Customers sign up and upload art; a seeded admin reviews every upload across customers, with status and delete.</p>
    </td>
  </tr>
</table>

<br />

## Stack

| Layer          | Choice                                 |
| :------------- | :------------------------------------- |
| Framework      | React 19 + React Router 7              |
| Build          | Vite 7                                 |
| Styling        | Tailwind CSS 3                         |
| Motion / icons | Framer Motion · lucide-react           |
| Persistence    | Browser `localStorage` (no backend)    |
| Hosting        | Vercel — SPA rewrites in `vercel.json` |

## Getting started

```bash
npm install
npm run dev        # Vite dev server on localhost
```

## Scripts

| Script                 | What it does                                   |
| :--------------------- | :--------------------------------------------- |
| `npm run dev`          | Start the Vite dev server                      |
| `npm run build`        | Production build to `dist/`                    |
| `npm run preview`      | Serve the built app locally                    |
| `npm run lint`         | Lint with ESLint                               |
| `npm run format`       | Format `src/` with Prettier                    |
| `npm run format:check` | Check formatting without writing changes       |

## Pages

| Route       | What it is                                                               |
| :---------- | :----------------------------------------------------------------------- |
| `/`         | Hero, product marquee, capabilities, process timeline, testimonials, FAQ |
| `/products` | Full catalog with category filters                                       |
| `/work`     | Portfolio strip of finished jobs                                         |
| `/about`    | Studio info page                                                         |
| `/contact`  | Contact page; the form is demo-only                                      |
| `/login`    | Mock auth backed by `localStorage`                                       |
| `/signup`   | Customer account creation                                                |
| `/account`  | Upload PNG/JPG/WEBP/SVG/GIF art (≤ 4 MB) and manage files                 |
| `/admin`    | Staff view of every uploaded file, with status + delete                  |

## How persistence works

There is no backend — a single `store.js` module is the whole data layer.

- **Everything is browser-local.** Users, the active session, and uploads are all read from and written to `localStorage`; nothing leaves the visitor's machine.
- **Uploads become data URLs.** Print-ready art is read client-side and stored inline, capped at **4 MB** per file with type validation for PNG, JPG, WEBP, SVG, and GIF.
- **An admin is seeded on first load.** The store guarantees a staff account exists, so the admin view works from the very first visit.
- **State is per-browser.** Because data lives in `localStorage`, it clears whenever the visitor clears site data.

## Demo credentials

A staff admin is seeded automatically on first load:

```
admin@impressivaprinting.com / admin123
```

Customers create their own accounts via **Sign up**.

## Project structure

```
src/app/
  components/    reusable UI (Nav, Marquee, ProductPlate, JobTracker, …)
  views/         pages (Home, Products, Work, Account, Admin, …)
  context/       auth context + provider
  hooks/         useAuth, useScrollProgress
  constants/     site config, product catalog, routes, content
  data/store.js  localStorage persistence layer
  utils/files.js upload validation (type + 4 MB cap)
public/          logo, favicon, brand imagery, release.json
```

## License

Private project — all rights reserved. Made by [TaylorURL](https://taylorurl.com).

<br />

<p align="center">
  <sub>Print Loud. Print Proud.</sub>
</p>
