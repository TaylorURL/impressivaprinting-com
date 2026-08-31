import { createClient } from '@supabase/supabase-js';

// The Supabase project behind the shop. The publishable key is safe to ship
// in the bundle — it only ever reaches the database through row level
// security — and the defaults keep a fresh clone working with zero config.
// Point at another project (a staging branch, say) via VITE_SUPABASE_URL and
// VITE_SUPABASE_PUBLISHABLE_KEY in a .env file.
const SUPABASE_URL =
  import.meta.env?.VITE_SUPABASE_URL || 'https://auzwqbakalnsxqwwklrh.supabase.co';
const SUPABASE_PUBLISHABLE_KEY =
  import.meta.env?.VITE_SUPABASE_PUBLISHABLE_KEY ||
  'sb_publishable_BW44zGUrTydcG9-Ph9OJVg_uDlzuVoq';

export const supabase = createClient(SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY);
