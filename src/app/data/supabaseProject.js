// Which Supabase project the shop talks to, and whether this browser could be
// carrying a session for it.
//
// This is its own module, and nothing from @supabase is allowed in it. The
// client is 210KB of JavaScript, and asking it whether anybody is signed in
// downloads, parses and evaluates all of it — at the priority a dynamic import
// gets, which on the landing page is the window the wordmark is painting in.
// The answer for a reader who has never signed in is sitting in local storage
// under a name the client derives from the project URL, so it is derived the
// same way here and read for a fraction of a millisecond instead.

export const SUPABASE_URL =
  import.meta.env?.VITE_SUPABASE_URL || 'https://auzwqbakalnsxqwwklrh.supabase.co';
export const SUPABASE_PUBLISHABLE_KEY =
  import.meta.env?.VITE_SUPABASE_PUBLISHABLE_KEY ||
  'sb_publishable_BW44zGUrTydcG9-Ph9OJVg_uDlzuVoq';

// supabase-js names its session entry after the project's subdomain. Deriving
// it from the same URL rather than writing it out means pointing
// VITE_SUPABASE_URL at a staging project moves both together.
const STORAGE_KEY = `sb-${new URL(SUPABASE_URL).hostname.split('.')[0]}-auth-token`;

// A session does not have to be in storage yet: a confirmation or recovery
// link arrives carrying one in the URL, and the client is what turns it into
// a session. These are the two shapes it comes in, implicit and PKCE, which
// are the two the client itself looks for.
function urlCarriesSession() {
  return (
    /[#&](access_token|error_description)=/.test(window.location.hash) ||
    /[?&]code=/.test(window.location.search)
  );
}

/**
 * Whether anything about this browser suggests a session to resolve.
 *
 * False is a firm answer — there is no session and nothing that could become
 * one — and it is the answer on essentially every arrival from search. True is
 * only ever "maybe", which is the right way round: being wrong that way costs
 * one early download, and being wrong the other way would leave somebody
 * already signed in looking at a signed-out page.
 *
 * @returns {boolean}
 */
export function mayHoldSession() {
  if (typeof window === 'undefined') return false;
  if (urlCarriesSession()) return true;
  try {
    return localStorage.getItem(STORAGE_KEY) !== null;
  } catch {
    // A store that cannot be read cannot rule a session out.
    return true;
  }
}
