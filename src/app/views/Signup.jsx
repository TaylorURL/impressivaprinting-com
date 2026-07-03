import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { UserPlus } from 'lucide-react';
import { useAuth } from '@hooks/useAuth.js';
import { ROUTES } from '@constants/routes.js';
import Button from '@components/Button.jsx';
import GlassCard from '@components/GlassCard.jsx';

const INPUT =
  'w-full rounded-xl border border-white/15 bg-white/5 px-4 py-3 text-sm text-white placeholder:text-white/35 outline-none transition-colors focus:border-cyan/60 focus:bg-white/[0.07]';

export default function Signup() {
  const { signup } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({ name: '', email: '', password: '', confirm: '' });
  const [error, setError] = useState('');

  const update = (key) => (e) => setForm((f) => ({ ...f, [key]: e.target.value }));

  const handleSubmit = (e) => {
    e.preventDefault();
    setError('');
    if (form.password.length < 6) {
      setError('Password needs at least 6 characters.');
      return;
    }
    if (form.password !== form.confirm) {
      setError('Passwords do not match.');
      return;
    }
    try {
      signup({ name: form.name, email: form.email, password: form.password });
      navigate(ROUTES.account, { replace: true });
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <div className="mx-auto flex max-w-md flex-col items-center px-4 pb-6 sm:px-6">
      <GlassCard className="w-full p-8">
        <span className="grid h-12 w-12 place-items-center rounded-2xl cyan-gradient text-ink-950">
          <UserPlus className="h-5 w-5" />
        </span>
        <h1 className="mt-5 spray text-4xl text-white">Start a Job</h1>
        <p className="mt-2 text-sm text-white/55">
          Create an account to upload art and track your prints.
        </p>

        <form onSubmit={handleSubmit} className="mt-7 space-y-4">
          <div>
            <label className="mb-1.5 block text-xs uppercase tracking-widest text-white/45">
              Name
            </label>
            <input
              className={INPUT}
              placeholder="Your name"
              value={form.name}
              onChange={update('name')}
              required
            />
          </div>
          <div>
            <label className="mb-1.5 block text-xs uppercase tracking-widest text-white/45">
              Email
            </label>
            <input
              type="email"
              className={INPUT}
              placeholder="you@email.com"
              value={form.email}
              onChange={update('email')}
              required
            />
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className="mb-1.5 block text-xs uppercase tracking-widest text-white/45">
                Password
              </label>
              <input
                type="password"
                className={INPUT}
                placeholder="••••••••"
                value={form.password}
                onChange={update('password')}
                required
              />
            </div>
            <div>
              <label className="mb-1.5 block text-xs uppercase tracking-widest text-white/45">
                Confirm
              </label>
              <input
                type="password"
                className={INPUT}
                placeholder="••••••••"
                value={form.confirm}
                onChange={update('confirm')}
                required
              />
            </div>
          </div>

          {error ? (
            <p className="rounded-xl border border-magenta/40 bg-magenta/10 px-4 py-2.5 text-sm text-white">
              {error}
            </p>
          ) : null}

          <Button as="button" type="submit" variant="cyan" size="lg" full>
            Create Account
          </Button>
        </form>

        <p className="mt-6 text-center text-sm text-white/50">
          Already rolling with us?{' '}
          <Link to={ROUTES.login} className="font-600 text-neon-cyan hover:underline">
            Log in
          </Link>
        </p>
      </GlassCard>
    </div>
  );
}
