import { useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight, MailCheck } from 'lucide-react';
import { useAuth } from '@hooks/useAuth.js';
import { ROUTES } from '@constants/routes.js';
import Button from '@components/Button.jsx';
import AuthShell from '@components/AuthShell.jsx';
import { fieldLabel, fieldInput } from '@components/Field.jsx';

const LABEL = fieldLabel();
const INPUT = fieldInput();

export default function ForgotPassword() {
  const { requestPasswordReset } = useAuth();
  const [email, setEmail] = useState('');
  const [sent, setSent] = useState(false);
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (submitting) return;
    setError('');
    setSubmitting(true);
    try {
      await requestPasswordReset(email);
      setSent(true);
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <AuthShell
      index="Access"
      kicker="Members"
      headline={
        <>
          Locked
          <br />
          Out?
        </>
      }
    >
      <span className="kicker text-flare">Reset Password</span>
      <h1 className="display mt-4 text-5xl text-paper-100">Get Back In</h1>

      {sent ? (
        <>
          <p className="mt-4 flex items-start gap-3 text-sm leading-relaxed text-paper-100/60">
            <MailCheck className="mt-1 h-4 w-4 shrink-0 text-flare" />
            <span>
              If an account exists for <span className="text-paper-100">{email}</span>, a reset link
              is on its way. Open it to choose a new password.
            </span>
          </p>
          <p className="mt-6 text-sm text-paper-100/50">
            Remembered it after all?{' '}
            <Link to={ROUTES.login} className="text-flare link-wipe">
              Log In
            </Link>
          </p>
        </>
      ) : (
        <>
          <p className="mt-3 text-sm text-paper-100/55">
            Enter your account email and we&apos;ll send you a link to choose a new password.
          </p>

          <form onSubmit={handleSubmit} className="mt-9 space-y-7">
            <div>
              <label className={LABEL} htmlFor="forgot-email">
                Email
              </label>
              <input
                id="forgot-email"
                name="email"
                type="email"
                inputMode="email"
                autoComplete="email"
                className={INPUT}
                aria-invalid={Boolean(error)}
                aria-describedby={error ? 'form-error' : undefined}
                placeholder="you@email.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
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

            <Button as="button" type="submit" variant="flare" size="lg" full disabled={submitting}>
              {submitting ? 'Sending…' : 'Send Reset Link'} <ArrowRight className="h-4 w-4" />
            </Button>
          </form>

          <p className="mt-6 text-sm text-paper-100/50">
            Back to{' '}
            <Link to={ROUTES.login} className="text-flare link-wipe">
              Log In
            </Link>
          </p>
        </>
      )}
    </AuthShell>
  );
}
