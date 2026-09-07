import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { ArrowRight } from 'lucide-react';
import { useAuth } from '@hooks/useAuth.js';
import { ROUTES } from '@constants/routes.js';
import Button from '@components/ui/Button.jsx';
import AuthShell from '@components/layout/AuthShell.jsx';
import { fieldLabel, fieldInput } from '@components/ui/Field.jsx';

const LABEL = fieldLabel();
const INPUT = fieldInput();

// Where the emailed recovery link lands. Opening the link signs the visitor
// in for this one purpose; without that session the form can only point back
// at the request page.
export default function ResetPassword() {
  const { isAuthed, ready, completePasswordReset } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({ password: '', confirm: '' });
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (submitting) return;
    setError('');
    if (form.password.length < 6) return setError('Password needs at least 6 characters.');
    if (form.password !== form.confirm) return setError('Passwords do not match.');
    setSubmitting(true);
    try {
      await completePasswordReset(form.password);
      navigate(ROUTES.portal, { replace: true });
    } catch (err) {
      setError(err.message);
      setSubmitting(false);
    }
  };

  return (
    <AuthShell
      index="Access"
      kicker="Members"
      headline={
        <>
          Fresh
          <br />
          Keys.
        </>
      }
    >
      <span className="kicker text-flare">Reset Password</span>
      <h1 className="display mt-4 text-5xl text-paper-100">Choose a New One</h1>

      {!ready ? null : !isAuthed ? (
        <>
          <p className="mt-3 text-sm leading-relaxed text-paper-100/55">
            This reset link has expired or was already used. Request a fresh one and try again.
          </p>
          <p className="mt-6 text-sm text-paper-100/50">
            <Link to={ROUTES.forgotPassword} className="text-flare link-wipe">
              Send a New Reset Link
            </Link>
          </p>
        </>
      ) : (
        <form onSubmit={handleSubmit} className="mt-9 space-y-7">
          <div>
            <label className={LABEL} htmlFor="reset-password">
              New Password
            </label>
            <input
              id="reset-password"
              name="new-password"
              type="password"
              autoComplete="new-password"
              className={INPUT}
              aria-invalid={Boolean(error)}
              aria-describedby={error ? 'form-error' : undefined}
              placeholder="••••••••"
              value={form.password}
              onChange={(e) => setForm((f) => ({ ...f, password: e.target.value }))}
              required
            />
          </div>
          <div>
            <label className={LABEL} htmlFor="reset-confirm">
              Confirm
            </label>
            <input
              id="reset-confirm"
              name="confirm-password"
              type="password"
              autoComplete="new-password"
              className={INPUT}
              aria-invalid={Boolean(error)}
              aria-describedby={error ? 'form-error' : undefined}
              placeholder="••••••••"
              value={form.confirm}
              onChange={(e) => setForm((f) => ({ ...f, confirm: e.target.value }))}
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
            {submitting ? 'Saving…' : 'Set Password'} <ArrowRight className="h-4 w-4" />
          </Button>
        </form>
      )}
    </AuthShell>
  );
}
