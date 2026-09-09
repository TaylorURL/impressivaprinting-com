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
 * The import carries the same recovery the routes in App.jsx carry, and it is
 * the one loader that was missing it. A route that fails to load costs a route;
 * this one costs the mount, so the reader keeps the first screen the document
 * drew and nothing on it answers — a page that looks loaded and is not. One
 * reload per entry is allowed, on an allowance of its own rather than the
 * routes', which settles a document left naming a build the host has replaced
 * and cannot become a loop. A store that cannot be read counts as an allowance
 * already spent, so a browser with storage closed to it never reloads at all.
 *
 * A SyntaxError takes no reload. The other failures here are a file that did not
 * arrive, and a second attempt against a fresh document is worth making; a file
 * that arrived and did not parse will not parse the next time either, so the
 * reload would buy the reader a flash of the same dead page. It is re-thrown
 * instead, and reaches the page reporter as the unhandled rejection it is.
 *
 * The refresh is announced on the way out for the reason chunk-recovery.js
 * announces it: the browser fails the module preload before the import rejects,
 * and the reporter is holding that failure waiting to hear whether the page is
 * about to fix itself.
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

// Named in index.html, where the reporter listens for it.
const REFRESH_EVENT = JSON.stringify('impressiva:build-refresh');
// The routes spend 'impressiva:build-refresh' in chunk-recovery.js. The entry
// keeps a mark of its own, so neither can take the other's one reload.
const RELOAD_MARK = JSON.stringify('impressiva:boot-refresh');
// The entry's filename carries a content hash, so a deploy that moves the
// bundle moves this and hands the next document an allowance of its own.
const BUILD = JSON.stringify(src);

const recover =
  `e=>{if(e instanceof SyntaxError)throw e;let s=true;` +
  `try{s=sessionStorage.getItem(${RELOAD_MARK})===${BUILD};` +
  `if(!s)sessionStorage.setItem(${RELOAD_MARK},${BUILD})}catch{s=true}` +
  `if(s)throw e;dispatchEvent(new Event(${REFRESH_EVENT}));location.reload()}`;

const boot = `    <script type="module">let b;const boot=()=>{if(b)return;b=1;import(${BUILD}).catch(${recover})};const hidden=()=>{if(document.visibilityState==='hidden')boot()};document.addEventListener('visibilitychange',hidden);requestAnimationFrame(()=>setTimeout(boot,0));hidden()</script>\n`;
const out = html
  .replace(tag, `${preload}${boot}`)
  .replaceAll('<link rel="modulepreload" crossorigin', '<link rel="modulepreload" fetchpriority="low" crossorigin');
if (/<link rel="modulepreload" (?!fetchpriority)/.test(out))
  throw new Error('paint-first: a module preload still outranks the first screen');
writeFileSync(file, out);
