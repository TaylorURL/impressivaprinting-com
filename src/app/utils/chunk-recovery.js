// Keeps a browser holding a build the host no longer serves off the error
// screen.
//
// Every route is a dynamic import of a chunk whose filename carries a content
// hash, and a deploy replaces those files with new names. A tab left open
// across a deploy asks for a filename the host no longer has: the import
// rejects, React.lazy turns the rejection into a render error, and the whole
// page becomes the error boundary's fallback for a visitor whose only problem
// is an old document.
//
// The document is what pins a build, so a reload settles it. One reload per
// build is allowed, which is enough for a chunk that moved and not enough for
// a chunk that is genuinely missing to become a loop. The allowance is
// recorded against the build that spent it, so the document a deploy hands
// back arrives with an allowance of its own.
//
// Nothing gives an allowance back, because more than one of these loaders is
// in flight at a time — a route chunk and the auth client, a portal layout and
// the page inside it — and a loader that succeeds has nothing to say about the
// one racing it that did not.
//
// The refresh is announced on the way out, because the page reporter sees the
// same missing chunk before this does. The browser fails the preload link
// first and that failure is a resource error with nothing attached to say the
// page is about to fix itself; the announcement is what says so.

const RELOAD_MARK = 'impressiva:build-refresh';

// Named in index.html, where the reporter listens for it.
const REFRESH_EVENT = 'impressiva:build-refresh';

// The build this document is running, named by the URL this module was loaded
// from. That name is content-hashed, and the names of the chunks it imports
// are part of what is hashed, so a deploy that moves any of them moves this
// too.
const BUILD = import.meta.url;

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

/**
 * Wraps a dynamic-import loader so a chunk missing from the served build
 * refreshes the page instead of failing the render.
 *
 * @param {() => Promise<unknown>} loader Dynamic import of a route or component.
 * @returns {() => Promise<unknown>} The same loader, with the refresh attached.
 */
export function withBuildRefresh(loader) {
  return () =>
    loader().catch((error) => {
      if (typeof window === 'undefined' || reloadSpent()) throw error;
      spendReload();
      window.dispatchEvent(new Event(REFRESH_EVENT));
      window.location.reload();
      // The reload is already under way. Settling this promise either way
      // would only put something on screen for the instant before it.
      return new Promise(() => {});
    });
}
