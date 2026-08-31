import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { ArrowRight, MailCheck } from 'lucide-react';
import { useAuth } from '@hooks/useAuth.js';
import { ROUTES } from '@constants/routes.js';
import Button from '@components/Button.jsx';
import AuthShell from '@components/AuthShell.jsx';
import { fieldLabel, fieldInput } from '@components/Field.jsx';

const LABEL = fieldLabel();
const INPUT = fieldInput();

// Both branches of the route are the same page, so they share one h1.
function PageTitle({ children }) {
  return <h1 className="display mt-4 text-5xl text-paper-100">{children}</h1>;
}

export default function Signup() {
  const { signup } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({ name: '', company: '', email: '', password: '', confirm: '' });
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [confirmationSent, setConfirmationSent] = useState(false);
  const update = (key) => (e) => setForm((f) => ({ ...f, [key]: e.target.value }));

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (submitting) return;
    setError('');
    if (form.password.length < 6) return setError('Password needs at least 6 characters.');
    if (form.password !== form.confirm) return setError('Passwords do not match.');
    setSubmitting(true);
    try {
      const result = await signup({
        name: form.name,
        company: form.company,
        email: form.email,
        password: form.password,
      });
      // The project can require email confirmation before the first sign-in;
      // in that case there's no session yet, just a link in their inbox.
      if (result?.confirmationRequired) {
        setConfirmationSent(true);
        return;
      }
      navigate(ROUTES.portal, { replace: true });
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  if (confirmationSent) {
    return (
      <AuthShell
        index="Access"
        kicker="New Client"
        headline={
          <>
            Check
            <br />
            Your Inbox.
          </>
        }
      >
        <span className="kicker text-flare">One More Step</span>
        <PageTitle>Confirm Your Email</PageTitle>
        <p className="mt-4 flex items-start gap-3 text-sm leading-relaxed text-paper-100/60">
          <MailCheck className="mt-1 h-4 w-4 shrink-0 text-flare" />
          <span>
            We sent a confirmation link to <span className="text-paper-100">{form.email}</span>.
            Open it, then log in to reach your portal.
          </span>
        </p>
        <p className="mt-6 text-sm text-paper-100/50">
          Already confirmed?{' '}
          <Link to={ROUTES.login} className="text-flare link-wipe">
            Log In
          </Link>
        </p>
      </AuthShell>
    );
  }

  return (
    <AuthShell
      index="Access"
      kicker="New Client"
      headline={
        <>
          Start
          <br />a Job.
        </>
      }
    >
      <span className="kicker text-flare">Create Account</span>
      <PageTitle>Get Started</PageTitle>
      <p className="mt-3 text-sm text-paper-100/55">Upload artwork and track your orders.</p>

      <form onSubmit={handleSubmit} className="mt-9 space-y-7">
        <div className="grid gap-7 sm:grid-cols-2">
          <div>
            <label className={LABEL} htmlFor="signup-name">
              Name
            </label>
            <input
              id="signup-name"
              name="name"
              type="text"
              autoComplete="name"
              className={INPUT}
              aria-invalid={Boolean(error)}
              aria-describedby={error ? 'form-error' : undefined}
              placeholder="Full name"
              value={form.name}
              onChange={update('name')}
              required
            />
          </div>
          <div>
            <label className={LABEL} htmlFor="signup-company">
              Company
            </label>
            <input
              id="signup-company"
              name="company"
              type="text"
              autoComplete="organization"
              className={INPUT}
              aria-invalid={Boolean(error)}
              aria-describedby={error ? 'form-error' : undefined}
              placeholder="Optional"
              value={form.company}
              onChange={update('company')}
            />
          </div>
        </div>
        <div>
          <label className={LABEL} htmlFor="signup-email">
            Email
          </label>
          <input
            id="signup-email"
            name="email"
            type="email"
            inputMode="email"
            autoComplete="email"
            className={INPUT}
            aria-invalid={Boolean(error)}
            aria-describedby={error ? 'form-error' : undefined}
            placeholder="you@email.com"
            value={form.email}
            onChange={update('email')}
            required
          />
        </div>
        <div className="grid gap-7 sm:grid-cols-2">
          <div>
            <label className={LABEL} htmlFor="signup-password">
              Password
            </label>
            <input
              id="signup-password"
              name="new-password"
              type="password"
              autoComplete="new-password"
              className={INPUT}
              aria-invalid={Boolean(error)}
              aria-describedby={error ? 'form-error' : undefined}
              placeholder="••••••••"
              value={form.password}
              onChange={update('password')}
              required
            />
          </div>
          <div>
            <label className={LABEL} htmlFor="signup-confirm">
              Confirm
            </label>
            <input
              id="signup-confirm"
              name="confirm-password"
              type="password"
              autoComplete="new-password"
              className={INPUT}
              aria-invalid={Boolean(error)}
              aria-describedby={error ? 'form-error' : undefined}
              placeholder="••••••••"
              value={form.confirm}
              onChange={update('confirm')}
              required
            />
          </div>
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

        <Button as="button" type="submit" variant="flare" size="lg" full disabled={submitting}>
          {submitting ? 'Creating account…' : 'Create Account'} <ArrowRight className="h-4 w-4" />
        </Button>
      </form>

      <p className="mt-6 text-sm text-paper-100/50">
        Already rolling with us?{' '}
        <Link to={ROUTES.login} className="text-flare link-wipe">
          Log In
        </Link>
      </p>
    </AuthShell>
  );
}
