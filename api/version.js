/* global process */
// The commit this deployment was built from, read from the page rather than
// from the host's record of it. Never cached: a cached answer would report a
// build that is no longer being served. The global is declared because this
// file runs on the host while the rest of the project runs in a browser, and
// the project's linter is configured for the latter.
export default function handler(request, response) {
  response.setHeader('Cache-Control', 'no-store, max-age=0');
  response.status(200).json({ build: process.env.VERCEL_GIT_COMMIT_SHA || 'dev' });
}
