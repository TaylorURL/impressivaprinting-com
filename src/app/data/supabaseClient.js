import { createClient } from '@supabase/supabase-js';
import { SUPABASE_PUBLISHABLE_KEY, SUPABASE_URL } from '@data/supabaseProject.js';

// The Supabase project behind the shop. The publishable key is safe to ship
// in the bundle — it only ever reaches the database through row level
// security — and the defaults keep a fresh clone working with zero config.
// Point at another project (a staging branch, say) via VITE_SUPABASE_URL and
// VITE_SUPABASE_PUBLISHABLE_KEY in a .env file. Both live in the module next
// door, which the entry can read without pulling this one in behind it.

export const supabase = createClient(SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY);
