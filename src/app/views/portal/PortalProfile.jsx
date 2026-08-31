import { useState } from 'react';
import { Check } from 'lucide-react';
import { useAuth } from '@hooks/useAuth.js';
import { store } from '@data/store.js';
import { formatDate } from '@utils/format.js';

import PanelPage from '@components/panel/PanelPage.jsx';
import { FIELD, LABEL, PanelCard, SpecList, PanelButton } from '@components/panel/ui.jsx';

function Flash({ show, children }) {
  if (!show) return null;
  return (
    <p className="mt-3 flex items-center gap-2 rounded-md border border-proc-y/30 bg-proc-y/10 px-3 py-2 text-xs text-paper-100">
      <Check className="h-3.5 w-3.5 text-proc-y" /> {children}
    </p>
  );
}

export default function PortalProfile() {
  const { user, refresh, changePassword } = useAuth();
  const [profile, setProfile] = useState({
    name: user.name,
    company: user.company || '',
    phone: user.phone || '',
  });
  const [passwords, setPasswords] = useState({ current: '', next: '', confirm: '' });
  const [profileSaved, setProfileSaved] = useState(false);
  const [profileError, setProfileError] = useState('');
  const [passwordSaved, setPasswordSaved] = useState(false);
  const [error, setError] = useState('');

  const saveProfile = async (e) => {
    e.preventDefault();
    setProfileSaved(false);
    setProfileError('');
    if (!profile.name.trim()) return;
    try {
      await store.updateUser(user.id, {
        name: profile.name.trim(),
        company: profile.company.trim(),
        phone: profile.phone.trim(),
      });
      refresh();
      setProfileSaved(true);
    } catch (err) {
      setProfileError(err.message);
    }
  };

  const savePassword = async (e) => {
    e.preventDefault();
    setError('');
    setPasswordSaved(false);
    if (passwords.next.length < 6) return setError('New password needs at least 6 characters.');
    if (passwords.next !== passwords.confirm) return setError('New passwords do not match.');
    try {
      await changePassword(passwords.current, passwords.next);
      setPasswords({ current: '', next: '', confirm: '' });
      setPasswordSaved(true);
    } catch (err) {
      setError(err.message);
    }
  };

  return (
    <PanelPage title="Profile" meta={`Since ${formatDate(user.createdAt)}`}>
      <div className="grid gap-5 lg:grid-cols-[1.4fr_1fr]">
        <div className="space-y-5">
          <PanelCard title="Contact">
            <form onSubmit={saveProfile} className="space-y-4">
              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <label className={LABEL} htmlFor="profile-name">
                    Name
                  </label>
                  <input
                    id="profile-name"
                    name="name"
                    type="text"
                    autoComplete="name"
                    className={FIELD}
                    value={profile.name}
                    onChange={(e) => setProfile((p) => ({ ...p, name: e.target.value }))}
                    required
                  />
                </div>
                <div>
                  <label className={LABEL} htmlFor="profile-company">
                    Company
                  </label>
                  <input
                    id="profile-company"
                    name="company"
                    type="text"
                    autoComplete="organization"
                    className={FIELD}
                    placeholder="Optional"
                    value={profile.company}
                    onChange={(e) => setProfile((p) => ({ ...p, company: e.target.value }))}
                  />
                </div>
                <div>
                  <label className={LABEL} htmlFor="profile-phone">
                    Phone
                  </label>
                  <input
                    id="profile-phone"
                    name="phone"
                    type="tel"
                    inputMode="tel"
                    autoComplete="tel"
                    className={FIELD}
                    placeholder="Optional"
                    value={profile.phone}
                    onChange={(e) => setProfile((p) => ({ ...p, phone: e.target.value }))}
                  />
                </div>
                <div>
                  <span className={LABEL}>Email</span>
                  <p className="px-3 py-2 text-[13px] text-paper-100/50">{user.email}</p>
                </div>
              </div>
              <PanelButton as="button" type="submit" variant="flare" size="sm">
                Save
              </PanelButton>
              {profileError ? (
                <p className="rounded-md border border-flare/30 bg-flare/10 px-3 py-2 text-xs text-paper-100">
                  {profileError}
                </p>
              ) : null}
              <Flash show={profileSaved}>Saved.</Flash>
            </form>
          </PanelCard>

          <PanelCard title="Password">
            <form onSubmit={savePassword} className="space-y-4">
              <div className="grid gap-4 sm:grid-cols-3">
                <div>
                  <label className={LABEL} htmlFor="pw-current">
                    Current
                  </label>
                  <input
                    id="pw-current"
                    name="current-password"
                    type="password"
                    autoComplete="current-password"
                    className={FIELD}
                    value={passwords.current}
                    onChange={(e) => setPasswords((p) => ({ ...p, current: e.target.value }))}
                    required
                  />
                </div>
                <div>
                  <label className={LABEL} htmlFor="pw-next">
                    New
                  </label>
                  <input
                    id="pw-next"
                    name="new-password"
                    type="password"
                    autoComplete="new-password"
                    className={FIELD}
                    value={passwords.next}
                    onChange={(e) => setPasswords((p) => ({ ...p, next: e.target.value }))}
                    required
                  />
                </div>
                <div>
                  <label className={LABEL} htmlFor="pw-confirm">
                    Confirm
                  </label>
                  <input
                    id="pw-confirm"
                    name="confirm-password"
                    type="password"
                    autoComplete="new-password"
                    className={FIELD}
                    value={passwords.confirm}
                    onChange={(e) => setPasswords((p) => ({ ...p, confirm: e.target.value }))}
                    required
                  />
                </div>
              </div>
              {error ? (
                <p className="rounded-md border border-flare/30 bg-flare/10 px-3 py-2 text-xs text-paper-100">
                  {error}
                </p>
              ) : null}
              <PanelButton as="button" type="submit" variant="outline" size="sm">
                Change Password
              </PanelButton>
              <Flash show={passwordSaved}>Password changed.</Flash>
            </form>
          </PanelCard>
        </div>

        <PanelCard title="Account" className="self-start">
          <SpecList
            items={[
              { k: 'Role', value: user.role === 'admin' ? 'Staff' : 'Client' },
              { k: 'Email', value: user.email },
              { k: 'Joined', value: formatDate(user.createdAt) },
              { k: 'Storage', value: 'Shop database' },
            ]}
          />
          <p className="mt-3 text-xs leading-relaxed text-paper-100/45">
            Your account, orders and artwork are stored in the shop&apos;s database. Sign in from
            any device to pick up where you left off.
          </p>
        </PanelCard>
      </div>
    </PanelPage>
  );
}
