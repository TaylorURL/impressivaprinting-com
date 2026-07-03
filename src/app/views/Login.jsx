import { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { LogIn } from 'lucide-react';
import { useAuth } from '@hooks/useAuth.js';
import { ROUTES } from '@constants/routes.js';
import Button from '@components/Button.jsx';
import GlassCard from '@components/GlassCard.jsx';

const INPUT =
  'w-full rounded-xl border border-white/15 bg-white/5 px-4 py-3 text-sm text-white placeholder:text-white/35 outline-none transition-colors focus:border-cyan/60 focus:bg-white/[0.07]';

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
      const dest = from || (user.role === 'admin' ? ROUTES.admin : ROUTES.account);
      navigate(dest, { replace: true });
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <div className="mx-auto flex max-w-md flex-col items-center px-4 pb-6 sm:px-6">
      <GlassCard className="w-full p-8">
        <span className="grid h-12 w-12 place-items-center rounded-2xl street-gradient text-ink-950">
          <LogIn className="h-5 w-5" />
        </span>
        <h1 className="mt-5 spray text-4xl text-white">Welcome Back</h1>
        <p className="mt-2 text-sm text-white/55">Log in to manage your jobs and drop new art.</p>

        <form onSubmit={handleSubmit} className="mt-7 space-y-4">
          <div>
            <label className="mb-1.5 block text-xs uppercase tracking-widest text-white/45">
              Email
            </label>
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
            <label className="mb-1.5 block text-xs uppercase tracking-widest text-white/45">
              Password
            </label>
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
            <p className="rounded-xl border border-magenta/40 bg-magenta/10 px-4 py-2.5 text-sm text-white">
              {error}
            </p>
          ) : null}

          <Button as="button" type="submit" variant="primary" size="lg" full>
            Log In
          </Button>
        </form>

        <p className="mt-6 text-center text-sm text-white/50">
          New here?{' '}
          <Link to={ROUTES.signup} className="font-600 text-neon-cyan hover:underline">
            Make an account
          </Link>
        </p>
      </GlassCard>

      <div className="mt-4 w-full rounded-2xl border border-white/10 bg-white/[0.03] px-5 py-4 text-xs text-white/50">
        <span className="font-700 uppercase tracking-widest text-white/40">Demo logins</span>
        <div className="mt-2 space-y-1">
          <div>
            Admin — <span className="text-neon-cyan">admin@impressivaprinting.com</span> / admin123
          </div>
          <div>Customer — sign up to create your own account.</div>
        </div>
      </div>
    </div>
  );
}
