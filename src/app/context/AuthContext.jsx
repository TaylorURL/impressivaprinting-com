import { useCallback, useEffect, useMemo, useState } from 'react';
import { store } from '@data/store.js';
import { AuthContext } from '@context/authContext.js';

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    setUser(store.getSession());
    setReady(true);
  }, []);

  const login = useCallback(({ email, password }) => {
    const authed = store.authenticate({ email, password });
    store.setSession(authed);
    setUser(authed);
    return authed;
  }, []);

  const signup = useCallback(({ name, email, password }) => {
    const created = store.register({ name, email, password });
    store.setSession(created);
    setUser(created);
    return created;
  }, []);

  const logout = useCallback(() => {
    store.setSession(null);
    setUser(null);
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
    }),
    [user, ready, login, signup, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
