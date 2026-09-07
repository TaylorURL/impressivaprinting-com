import { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { ArrowRight } from 'lucide-react';
import { useAuth } from '@hooks/useAuth.js';
import { ROUTES } from '@constants/routes.js';
import Button from '@components/ui/Button.jsx';
import AuthShell from '@components/layout/AuthShell.jsx';
import { fieldLabel, fieldInput } from '@components/ui/Field.jsx';

const LABEL = fieldLabel();
const INPUT = fieldInput();

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [form, setForm] = useState({ email: '', password: '' });
  const [error, setError] = useState('');
  const from = location.state?.from;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    try {
      const user = await login(form);
      navigate(from || (user.role === 'admin' ? ROUTES.admin : ROUTES.portal), { replace: true });
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <AuthShell
      index="Access"
      kicker="Members"
      headline={
        <>
          Welcome
          <br />
          Back.
        </>
      }
    >
      <span className="kicker text-flare">Log In</span>
      <h1 className="display mt-4 text-5xl text-paper-100">Your Account</h1>
      <p className="mt-3 text-sm text-paper-100/55">Manage your orders and upload new artwork.</p>

      <form onSubmit={handleSubmit} className="mt-9 space-y-7">
        <div>
          <label className={LABEL} htmlFor="login-email">
            Email
          </label>
          <input
            id="login-email"
            name="email"
            type="email"
            inputMode="email"
            autoComplete="email"
            className={INPUT}
            aria-invalid={Boolean(error)}
            aria-describedby={error ? 'form-error' : undefined}
            placeholder="name@example.com"
            value={form.email}
            onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))}
            required
          />
        </div>
        <div>
          <div className="mb-2 flex items-baseline justify-between">
            <label className={`${LABEL} mb-0`} htmlFor="login-password">
              Password
            </label>
            <Link
              to={ROUTES.forgotPassword}
              className="text-xs text-paper-100/45 transition-colors hover:text-flare"
            >
              Forgot password?
            </Link>
          </div>
          <input
            id="login-password"
            name="password"
            type="password"
            autoComplete="current-password"
            className={INPUT}
            aria-invalid={Boolean(error)}
            aria-describedby={error ? 'form-error' : undefined}
            placeholder="••••••••"
            value={form.password}
            onChange={(e) => setForm((f) => ({ ...f, password: e.target.value }))}
            required
          />
        </div>

        {error ? (
          <p
            id="form-error"
            role="alert"
            className="spec border-l-2 border-flare bg-flare/10 px-4 py-3 text-xs text-paper-100"
          >
            {error}
          </p>
        ) : null}

        <Button as="button" type="submit" variant="flare" size="lg" full>
          Log In <ArrowRight className="h-4 w-4" />
        </Button>
      </form>

      <p className="mt-6 text-sm text-paper-100/50">
        New here?{' '}
        <Link to={ROUTES.signup} className="text-flare link-wipe">
          Make an Account
        </Link>
      </p>
    </AuthShell>
  );
}
