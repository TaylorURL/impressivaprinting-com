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
 * tag. An inline module in its place asks for the bundle as a task queued from
 * the first frame's rendering, which is the earliest moment the bundle can no
 * longer hold that frame back.
 *
 * A hidden document takes the other branch and boots at once. A tab in the
 * background produces no frames at all, so left to the frame callback alone the
 * chunks would arrive and nothing would mount until somebody fronted the tab.
 * It is the right branch rather than a fallback: the frame gate exists to keep
 * the bundle off a paint, and a document nobody is looking at has no paint to
 * keep it off. A timer instead of the visibility test would arm on every load
 * and, on a phone connection where the first frame lands around a second in,
 * would be what booted the app on nearly all of them.
 *
 * The preloads are also taken off the top of the queue. A module preload is
 * asked for at the same priority as the wordmark and the faces the first
 * screen sets, and there are four of them carrying a hundred kilobytes, so on
 * a phone connection the mark the page is measured on waits behind code that
 * nothing has painted yet. Marked low, the same files still arrive, and the
 * first screen has the connection to itself until they do.
 *
 * Run by `npm run build`, after the bundle exists.
 */
import { readFileSync, writeFileSync } from 'node:fs';

const file = 'dist/index.html';
const html = readFileSync(file, 'utf8');
const entry = html.match(/^[ \t]*<script type="module" crossorigin src="([^"]+)"><\/script>\n/m);
if (!entry) throw new Error('paint-first: dist/index.html carries no module entry');
const [tag, src] = entry;
const preload = `    <link rel="modulepreload" fetchpriority="low" crossorigin href="${src}" />\n`;
const boot = `    <script type="module">let b;const boot=()=>{if(b)return;b=1;import(${JSON.stringify(src)})};const hidden=()=>{if(document.visibilityState==='hidden')boot()};document.addEventListener('visibilitychange',hidden);requestAnimationFrame(()=>setTimeout(boot,0));hidden()</script>\n`;
const out = html
  .replace(tag, `${preload}${boot}`)
  .replaceAll('<link rel="modulepreload" crossorigin', '<link rel="modulepreload" fetchpriority="low" crossorigin');
if (/<link rel="modulepreload" (?!fetchpriority)/.test(out))
  throw new Error('paint-first: a module preload still outranks the first screen');
writeFileSync(file, out);
