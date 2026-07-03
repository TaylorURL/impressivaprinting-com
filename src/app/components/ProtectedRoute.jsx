import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '@hooks/useAuth.js';
import { ROUTES } from '@constants/routes.js';

export default function ProtectedRoute({ children, adminOnly = false }) {
  const { isAuthed, isAdmin, ready } = useAuth();
  const location = useLocation();

  if (!ready) return null;

  if (!isAuthed) {
    return <Navigate to={ROUTES.login} state={{ from: location.pathname }} replace />;
  }
  if (adminOnly && !isAdmin) {
    return <Navigate to={ROUTES.account} replace />;
  }
  return children;
}
