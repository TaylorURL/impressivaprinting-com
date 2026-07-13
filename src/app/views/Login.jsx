import { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { ArrowRight } from 'lucide-react';
import { useAuth } from '@hooks/useAuth.js';
import { ROUTES } from '@constants/routes.js';
import Button from '@components/Button.jsx';
import AuthShell from '@components/AuthShell.jsx';

const LABEL = 'kicker mb-2 block text-paper-100/45';
const INPUT =
  'w-full border-b border-paper-100/20 bg-transparent py-3 text-paper-100 placeholder:text-paper-100/30 outline-none transition-colors focus:border-flare';

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [form, setForm] = useState({ email: '', password: '' });
  const [error, setError] = useState('');
  const from = location.state?.from;

  const handleSubmit = (e) => {
    e.preventDefault();
    setError('');
    try {
      const user = login(form);
      navigate(from || (user.role === 'admin' ? ROUTES.admin : ROUTES.account), { replace: true });
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <AuthShell
      index="No. 05 — Access"
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
          <label className={LABEL}>Email</label>
          <input
            type="email"
            className={INPUT}
            placeholder="you@email.com"
            value={form.email}
            onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))}
            required
          />
        </div>
        <div>
          <label className={LABEL}>Password</label>
          <input
            type="password"
            className={INPUT}
            placeholder="••••••••"
            value={form.password}
            onChange={(e) => setForm((f) => ({ ...f, password: e.target.value }))}
            required
          />
        </div>

        {error ? (
          <p className="spec border-l-2 border-flare bg-flare/10 px-4 py-2.5 text-xs text-paper-100">
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
          Make an account
        </Link>
      </p>

      <div className="mt-8 border-t border-paper-100/12 pt-5">
        <span className="kicker text-paper-100/40">Demo Access</span>
        <div className="spec mt-3 space-y-1 text-xs text-paper-100/50">
          <div>
            Admin — <span className="text-proc-c">admin@impressivaprinting.com</span> / admin123
          </div>
          <div>Customer — sign up to create your own.</div>
        </div>
      </div>
    </AuthShell>
  );
}
