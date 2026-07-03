import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { ArrowRight } from 'lucide-react';
import { useAuth } from '@hooks/useAuth.js';
import { ROUTES } from '@constants/routes.js';
import Button from '@components/Button.jsx';
import AuthShell from '@components/AuthShell.jsx';

const LABEL = 'kicker mb-2 block text-paper-100/45';
const INPUT =
  'w-full border-b border-paper-100/20 bg-transparent py-3 text-paper-100 placeholder:text-paper-100/30 outline-none transition-colors focus:border-flare';

export default function Signup() {
  const { signup } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({ name: '', email: '', password: '', confirm: '' });
  const [error, setError] = useState('');
  const update = (key) => (e) => setForm((f) => ({ ...f, [key]: e.target.value }));

  const handleSubmit = (e) => {
    e.preventDefault();
    setError('');
    if (form.password.length < 6) return setError('Password needs at least 6 characters.');
    if (form.password !== form.confirm) return setError('Passwords do not match.');
    try {
      signup({ name: form.name, email: form.email, password: form.password });
      navigate(ROUTES.account, { replace: true });
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <AuthShell
      index="No. 05 — Access"
      kicker="New Client"
      headline={
        <>
          Start
          <br />a Job.
        </>
      }
    >
      <span className="kicker text-flare">Create Account</span>
      <h1 className="display mt-4 text-5xl text-paper-100">Roll With Us</h1>
      <p className="mt-3 text-sm text-paper-100/55">Upload art and track your prints.</p>

      <form onSubmit={handleSubmit} className="mt-9 space-y-7">
        <div>
          <label className={LABEL}>Name</label>
          <input
            className={INPUT}
            placeholder="Your name"
            value={form.name}
            onChange={update('name')}
            required
          />
        </div>
        <div>
          <label className={LABEL}>Email</label>
          <input
            type="email"
            className={INPUT}
            placeholder="you@email.com"
            value={form.email}
            onChange={update('email')}
            required
          />
        </div>
        <div className="grid gap-7 sm:grid-cols-2">
          <div>
            <label className={LABEL}>Password</label>
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
            <label className={LABEL}>Confirm</label>
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
          <p className="spec border-l-2 border-flare bg-flare/10 px-4 py-2.5 text-xs text-paper-100">
            {error}
          </p>
        ) : null}

        <Button as="button" type="submit" variant="flare" size="lg" full>
          Create Account <ArrowRight className="h-4 w-4" />
        </Button>
      </form>

      <p className="mt-6 text-sm text-paper-100/50">
        Already rolling with us?{' '}
        <Link to={ROUTES.login} className="text-flare link-wipe">
          Log in
        </Link>
      </p>
    </AuthShell>
  );
}
