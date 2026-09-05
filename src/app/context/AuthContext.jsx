import { startTransition, useCallback, useEffect, useMemo, useState } from 'react';
import { AuthContext } from '@context/authContext.js';

// The auth client and the data layer over it are fifty-odd kilobytes of code
// that a reader who never signs in never runs. Named as static imports they
// join the entry's own dependencies, so the browser has to fetch, parse and
// evaluate all of it before React is allowed to mount — the shop's first
// screen waits on a session check for a session almost nobody has. Reached
// through these accessors instead, the same modules arrive after the mount
// rather than in front of it. Everything below that touches them is already
// async, so awaiting one module more costs the signed-in path a single fetch
// and costs the first screen nothing. Each accessor keeps its own promise,
// which is what makes a second caller reuse the first caller's module
// instead of racing it.
let clientModule;
const getSupabase = () =>
  (clientModule ??= import('@data/supabaseClient.js')).then((m) => m.supabase);

let storeModule;
const getStore = () => (storeModule ??= import('@data/store.js')).then((m) => m.store);

// Supabase Auth error strings, translated into the shop's voice.
function friendlyAuthError(error) {
  const message = error?.message || '';
  if (/invalid login credentials/i.test(message)) return 'Wrong email or password.';
  if (/email not confirmed/i.test(message)) {
    return 'Confirm your email first. The link is in your inbox.';
  }
  if (/already registered/i.test(message)) return 'An account with that email already exists.';
  if (/email rate limit/i.test(message)) {
    return 'The shop has sent too many emails this hour. Try again a little later.';
  }
  if (/rate limit|too many/i.test(message))
    return 'Too many attempts. Wait a minute and try again.';
  return message || 'Something went wrong. Try again.';
}

export function AuthProvider({ children }) {
  // The Supabase session says who is signed in; `user` is their profile row,
  // which carries the role the panels gate on.
  const [sessionUserId, setSessionUserId] = useState(null);
  const [user, setUser] = useState(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    let active = true;
    // The subscription cannot be handed back from the effect body, because
    // the client it comes from has not arrived yet. Cleanup takes it through
    // this binding instead, and an unmount that beats the module leaves
    // `active` false, so no subscription is ever opened to leak.
    let unsubscribe;
    getSupabase().then((supabase) => {
      if (!active) return;
      // getClaims verifies the token's signature; getSession reports whatever
      // storage holds, which is user input where the role gates the panels.
      supabase.auth.getClaims().then(({ data }) => {
        if (!active) return;
        setSessionUserId(data?.claims?.sub ?? null);
        // With no session there is no profile to wait for.
        if (!data?.claims) setReady(true);
      });
      const { data: subscription } = supabase.auth.onAuthStateChange((_event, session) => {
        // No supabase calls in this callback — the client holds its auth lock
        // while it runs. The profile loads in the effect below instead.
        setSessionUserId(session?.user?.id ?? null);
      });
      unsubscribe = () => subscription.subscription.unsubscribe();
    });
    return () => {
      active = false;
      if (unsubscribe) unsubscribe();
    };
  }, []);

  // Resolve the session to a profile whenever the signed-in user changes.
  useEffect(() => {
    if (!sessionUserId) {
      setUser(null);
      return undefined;
    }
    let active = true;
    getStore()
      .then((store) => store.getProfile(sessionUserId))
      .then((profile) => {
        if (!active) return;
        if (profile) {
          setUser(profile);
        } else {
          // A session for an account that no longer exists (removed customer).
          getSupabase().then((supabase) => supabase.auth.signOut());
          setUser(null);
        }
      })
      .catch(() => {})
      .finally(() => {
        if (active) setReady(true);
      });
    return () => {
      active = false;
    };
  }, [sessionUserId]);

  const login = useCallback(async ({ email, password }) => {
    const supabase = await getSupabase();
    const { data, error } = await supabase.auth.signInWithPassword({
      email: email.trim(),
      password,
    });
    if (error) throw new Error(friendlyAuthError(error));
    const store = await getStore();
    const profile = await store.getProfile(data.user.id);
    if (!profile) {
      await supabase.auth.signOut();
      throw new Error('This account no longer exists.');
    }
    setUser(profile);
    return profile;
  }, []);

  // Signup may or may not open a session, depending on whether the project
  // requires email confirmation — callers branch on `confirmationRequired`.
  const signup = useCallback(async ({ name, email, password, company = '' }) => {
    const supabase = await getSupabase();
    const { data, error } = await supabase.auth.signUp({
      email: email.trim(),
      password,
      options: {
        data: { name: name.trim(), company: company.trim() },
        emailRedirectTo: `${window.location.origin}/login`,
      },
    });
    if (error) throw new Error(friendlyAuthError(error));
    // Supabase obfuscates signups against taken emails as a user with no
    // identities rather than an error.
    if (data.user && data.user.identities?.length === 0) {
      throw new Error('An account with that email already exists.');
    }
    if (!data.session) return { confirmationRequired: true };
    const store = await getStore();
    const profile = await store.getProfile(data.user.id);
    setUser(profile);
    return profile;
  }, []);

  // The state clear rides the same transition as the router's post-logout
  // navigation. A sync clear re-renders the protected layout while the URL
  // still points at it, and ProtectedRoute's login redirect then beats the
  // intended "back to home" navigation. The server-side sign-out finishes
  // in the background.
  const logout = useCallback(() => {
    getSupabase().then((supabase) => supabase.auth.signOut());
    startTransition(() => setUser(null));
  }, []);

  // Re-resolves the profile, so edits made through the store show up in
  // context immediately.
  const refresh = useCallback(() => {
    if (!sessionUserId) return;
    getStore()
      .then((store) => store.getProfile(sessionUserId))
      .then((profile) => profile && setUser(profile))
      .catch(() => {});
  }, [sessionUserId]);

  // Supabase doesn't check the old password on update, so prove it first
  // with a fresh sign-in.
  const changePassword = useCallback(
    async (currentPassword, nextPassword) => {
      if (!user?.email) throw new Error('Not signed in.');
      const supabase = await getSupabase();
      const { error: reauthError } = await supabase.auth.signInWithPassword({
        email: user.email,
        password: currentPassword,
      });
      if (reauthError) throw new Error('Current password is wrong.');
      const { error } = await supabase.auth.updateUser({ password: nextPassword });
      if (error) throw new Error(friendlyAuthError(error));
    },
    [user?.email],
  );

  const requestPasswordReset = useCallback(async (email) => {
    const supabase = await getSupabase();
    const { error } = await supabase.auth.resetPasswordForEmail(email.trim(), {
      redirectTo: `${window.location.origin}/reset-password`,
    });
    if (error) throw new Error(friendlyAuthError(error));
  }, []);

  // Used on the recovery landing page, where the emailed link has already
  // opened a session.
  const completePasswordReset = useCallback(async (password) => {
    const supabase = await getSupabase();
    const { error } = await supabase.auth.updateUser({ password });
    if (error) throw new Error(friendlyAuthError(error));
  }, []);

  const value = useMemo(
    () => ({
      user,
      ready,
      isAuthed: Boolean(user),
      isAdmin: user?.role === 'admin',
      login,
      signup,
      logout,
      refresh,
      changePassword,
      requestPasswordReset,
      completePasswordReset,
    }),
    [
      user,
      ready,
      login,
      signup,
      logout,
      refresh,
      changePassword,
      requestPasswordReset,
      completePasswordReset,
    ],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
