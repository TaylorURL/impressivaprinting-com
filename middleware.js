/**
 * Holds the site offline while TaylorURL has it paused, and lets every page
 * through the rest of the time.
 *
 * TaylorURL pauses a client's site once an invoice is a week past due and
 * lifts the pause a few minutes after it is paid. The answer comes from its
 * own endpoint, and anything short of a clear yes from there - an error, a
 * slow reply, no reply - leaves the site up, so trouble on that side never
 * takes this site down with it.
 */

const SITE = 'impressivaprinting.com';
const STATUS_URL = `https://www.taylorurl.com/api/site-status?site=${SITE}`;

/** How long a page waits on the answer before it loads anyway. */
const WAIT_MS = 1500;

/** How long an answer is trusted before the question is asked again. */
const REMEMBER_MS = 60 * 1000;

export const config = {
  // Pages, not files: a path ending in an extension is a script, a style, an
  // image or a font, and none of those needs the question asked.
  matcher: ['/((?!.*\\.[^/]*$).*)'],
};

let answer = { paused: false, until: 0 };

async function isPaused() {
  const now = Date.now();
  if (now < answer.until) return answer.paused;
  let paused = false;
  try {
    const response = await fetch(STATUS_URL, { signal: AbortSignal.timeout(WAIT_MS) });
    if (response.ok) paused = (await response.json()).paused === true;
  } catch {
    // Unreachable or too slow to wait for: the site stays up.
  }
  answer = { paused, until: now + REMEMBER_MS };
  return paused;
}

const PAGE = `<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <meta name="robots" content="noindex" />
    <title>Temporarily unavailable</title>
    <style>
      :root { color-scheme: light dark; }
      body { margin: 0; min-height: 100vh; display: grid; place-items: center; background: #fafafa; color: #1a1a1a; font-family: system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif; }
      main { max-width: 32rem; padding: 2rem 1.5rem; text-align: center; }
      h1 { margin: 0 0 0.75rem; font-size: 1.5rem; line-height: 1.3; }
      p { margin: 0 0 1rem; color: #4a4a4a; line-height: 1.6; }
      .owner { font-size: 0.875rem; color: #6a6a6a; }
      a { color: inherit; }
      @media (prefers-color-scheme: dark) {
        body { background: #141414; color: #f0f0f0; }
        p { color: #c4c4c4; }
        .owner { color: #9a9a9a; }
      }
    </style>
  </head>
  <body>
    <main>
      <h1>This site is temporarily unavailable</h1>
      <p>Please check back soon.</p>
      <p class="owner">If this is your website, call TaylorURL at <a href="tel:+12818628687">(281) 862-8687</a>.</p>
    </main>
  </body>
</html>
`;

export default async function middleware() {
  if (!(await isPaused())) return;
  return new Response(PAGE, {
    status: 503,
    headers: {
      'Content-Type': 'text/html; charset=utf-8',
      'Cache-Control': 'no-store',
      'Retry-After': '3600',
      // How TaylorURL's own monitoring tells a pause from an outage.
      'X-Site-Paused': '1',
    },
  });
}
