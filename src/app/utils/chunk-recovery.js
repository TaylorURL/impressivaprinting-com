// Keeps a browser off a blank page when a route's chunk does not arrive.
//
// Every route is a dynamic import of a chunk whose filename carries a content
// hash. Two different things make one of those imports reject, and they want
// opposite answers:
//
//   - The request was lost. The file is on the host, the connection dropped it,
//     and asking again is the whole fix. Reloading the document for this is
//     worse than useless: it throws away a page the reader was on to go back
//     over the same connection that just failed.
//   - A deploy replaced the file. The document is pinned to a build the host no
//     longer serves, so no number of retries can produce the file and only a
//     reload - which fetches a fresh document - can.
//
// So the loader asks again, a few times, with a short wait between tries; and
// only then, and only if the served document no longer names the build this one
// is running, does it reload. That check is also what stops an offline client
// being put in a reload loop: a browser that cannot reach the host cannot
// confirm a new build, so it is never told to reload, and it keeps the page it
// has.
//
// One reload per build is allowed on top of that, recorded against the build
// that spent it, so the document a deploy hands back arrives with an allowance
// of its own. Nothing gives an allowance back, because more than one of these
// loaders is in flight at a time - a route chunk and the auth client, a portal
// layout and the page inside it - and a loader that succeeds has nothing to say
// about the one racing it that did not.
//
// What is left when all of that fails is a rejected import, and RouteErrorBoundary
// is what catches it. Before this, nothing did: the rejection became a render
// error with no boundary above it, React tore the whole tree down, and the
// reader was left looking at an empty document while the console took an
// uncaught TypeError. The reader now gets a page that says the page did not
// load and offers to try again.
//
// The refresh is announced on the way out, because the page reporter sees the
// same missing chunk before this does. The browser fails the preload link first
// and that failure is a resource error with nothing attached to say the page is
// about to fix itself; the announcement is what says so.

const RELOAD_MARK = 'impressiva:build-refresh';

// Named in index.html, where the reporter listens for it.
const REFRESH_EVENT = 'impressiva:build-refresh';

// Three asks in total, which covers a request lost in a bad second without
// keeping a reader in front of a placeholder when the file is genuinely gone.
const TRIES = 3;

// Short enough that the retry is invisible against a chunk arriving slowly,
// long enough to be on the other side of a hiccup.
const BACKOFF_MS = [120, 480];

// The build this document is running, named by the URL this module was loaded
// from. That name is content-hashed, and the names of the chunks it imports are
// part of what is hashed, so a deploy that moves any of them moves this too.
const BUILD = import.meta.url;

// The served document names the current build's entry in its preload and in the
// script that boots it, so this filename is what to look for in it.
const BUILD_FILE = BUILD.slice(BUILD.lastIndexOf('/') + 1);

// A retry has to ask for a different URL than the one that failed. The browser
// keeps a module map, and a specifier that failed to load stays failed in it:
// importing the same URL again rejects out of that record without a request
// ever leaving the machine. Verified here against the built site - the chunk
// was dropped once, the loader asked twice more, and the server saw one single
// ask. So the retry re-imports the chunk's own URL with a parameter on it,
// which is a URL the map has nothing against. Only the route module itself is
// instantiated a second time; its imports are resolved relative to the chunk
// and come off the instances already loaded.
//
// The URL comes out of the failure, which is where the browser puts it:
// "Failed to fetch dynamically imported module: https://host/assets/Work-x.js".
function chunkUrlFrom(error) {
  const found = /https?:\/\/[^\s"')]+\.js(\?[^\s"')]*)?/.exec(String(error?.message || ''));
  return found ? found[0] : null;
}

function wait(ms) {
  return new Promise((resolve) => {
    setTimeout(resolve, ms);
  });
}

// A store that cannot be read cannot gate anything, and an ungated reload over
// a chunk that will never arrive never stops, so an unreadable store counts as
// an allowance already spent.
function reloadSpent() {
  try {
    return sessionStorage.getItem(RELOAD_MARK) === BUILD;
  } catch {
    return true;
  }
}

function spendReload() {
  try {
    sessionStorage.setItem(RELOAD_MARK, BUILD);
  } catch {
    // Nothing to spend when the store is closed to us.
  }
}

// Whether the host has moved on from the build this document is running. Asked
// of the document rather than of the missing chunk: the chunk is absent either
// way, and only the document says which build is current. Anything that is not
// a plain answer of "this build is gone" counts as not stale, so a client that
// cannot reach the host keeps the page it is on.
async function buildReplaced() {
  if (typeof fetch !== 'function') return false;
  try {
    const response = await fetch(new URL('/', window.location.href), {
      cache: 'no-store',
      credentials: 'same-origin',
    });
    if (!response.ok) return false;
    return !(await response.text()).includes(BUILD_FILE);
  } catch {
    return false;
  }
}

/**
 * Wraps a dynamic-import loader so a chunk that does not arrive is asked for
 * again, and a chunk missing because the build moved refreshes the page.
 *
 * @param {() => Promise<unknown>} loader Dynamic import of a route or component.
 * @returns {() => Promise<unknown>} The same loader, with the recovery attached.
 */
export function withBuildRefresh(loader) {
  return async () => {
    let failure;
    for (let attempt = 0; attempt < TRIES; attempt += 1) {
      try {
        if (attempt === 0) return await loader();
        const url = chunkUrlFrom(failure);
        if (!url) break;
        await wait(BACKOFF_MS[attempt - 1] ?? BACKOFF_MS[BACKOFF_MS.length - 1]);
        return await import(
          /* @vite-ignore */ `${url}${url.includes('?') ? '&' : '?'}retry=${attempt}`
        );
      } catch (error) {
        failure = error;
      }
    }

    if (typeof window === 'undefined' || reloadSpent()) throw failure;
    if (!(await buildReplaced())) throw failure;

    spendReload();
    window.dispatchEvent(new Event(REFRESH_EVENT));
    window.location.reload();
    // The reload is already under way. Settling this promise either way would
    // only put something on screen for the instant before it.
    return new Promise(() => {});
  };
}
