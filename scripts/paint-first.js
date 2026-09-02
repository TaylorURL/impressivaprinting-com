/*
 * Runs the bundle after the first frame rather than before it.
 *
 * The document carries the first screen as markup, so its first frame owes
 * the bundle nothing. A module script is deferred, which only means it waits
 * for the parser: it runs the moment parsing ends, and on a slow phone that
 * moment arrives before the browser has found a frame to paint the document
 * in. The page then sits blank while the bundle draws over markup nobody has
 * been shown, and the whole download is charged to the first paint.
 *
 * The entry keeps its early fetch, as a module preload, and loses its script
 * tag. An inline module in its place asks for the bundle one frame after the
 * first, which is the first frame the document can have been painted in and
 * the earliest the bundle can no longer hold it back.
 *
 * Run by `npm run build`, after the bundle exists.
 */
import { readFileSync, writeFileSync } from 'node:fs';

const file = 'dist/index.html';
const html = readFileSync(file, 'utf8');
const entry = html.match(/^[ \t]*<script type="module" crossorigin src="([^"]+)"><\/script>\n/m);
if (!entry) throw new Error('paint-first: dist/index.html carries no module entry');
const [tag, src] = entry;
const preload = `    <link rel="modulepreload" crossorigin href="${src}" />\n`;
const boot = `    <script type="module">requestAnimationFrame(() => requestAnimationFrame(() => import(${JSON.stringify(src)})))</script>\n`;
writeFileSync(file, html.replace(tag, `${preload}${boot}`));
