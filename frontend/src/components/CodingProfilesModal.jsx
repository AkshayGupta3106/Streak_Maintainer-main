import { useEffect, useState } from 'react';

import { getCodingProfile, updateCodingProfile } from '../api/profiles';
import ModalShell from './ModalShell';

export default function CodingProfilesModal({ open, onClose, onProfileUpdated }) {
  const [leetcode, setLeetcode] = useState('');
  const [codeforces, setCodeforces] = useState('');
  const [codechef, setCodechef] = useState('');
  const [gfg, setGfg] = useState('');
  const [sendEmail, setSendEmail] = useState(true);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  useEffect(() => {
    if (!open) {
      return;
    }

    async function load() {
      setLoading(true);
      setError('');
      try {
        const profile = await getCodingProfile();
        setLeetcode(profile.leetcode_username || '');
        setCodeforces(profile.codeforces_username || '');
        setCodechef(profile.codechef_username || '');
        setGfg(profile.geeksforgeeks_username || '');
        setSendEmail(profile.send_email_reminders ?? true);
      } catch {
        setError('Failed to load coding profiles');
      } finally {
        setLoading(false);
      }
    }

    load();
  }, [open]);

  if (!open) {
    return null;
  }

  const handleSubmit = async (event) => {
    event.preventDefault();
    setSaving(true);
    setError('');
    setSuccess('');

    try {
      const updated = await updateCodingProfile({
        leetcode_username: leetcode.trim(),
        codeforces_username: codeforces.trim(),
        codechef_username: codechef.trim(),
        geeksforgeeks_username: gfg.trim(),
        phone_number: '',
        send_email_reminders: sendEmail,
        send_whatsapp_reminders: false,
      });
      setSuccess('Settings saved successfully! Returning to dashboard...');
      onProfileUpdated?.(updated);
      setTimeout(() => {
        setSuccess('');
        onClose();
      }, 1200);
    } catch {
      setError('Failed to save settings, try again.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <ModalShell title="Coding Profiles & Contests" onClose={onClose} wide>
      {error ? <div className="banner banner-error">{error}</div> : null}
      {success ? <div className="banner banner--notice">{success}</div> : null}
      {loading ? <p className="empty-copy">Loading profiles…</p> : null}

      {!loading && (
        <form className="stack-form" onSubmit={handleSubmit}>
          <div className="task-panel__header">
            <h3>Connected Platforms</h3>
            <p className="muted">Enter your handles/usernames to load upcoming contests from these platforms.</p>
          </div>

          <div className="form-row split">
            <label>
              LeetCode Username
              <input
                value={leetcode}
                onChange={(event) => setLeetcode(event.target.value)}
                placeholder="LeetCode Handle"
              />
            </label>
            <label>
              Codeforces Username
              <input
                value={codeforces}
                onChange={(event) => setCodeforces(event.target.value)}
                placeholder="Codeforces Handle"
              />
            </label>
          </div>

          <div className="form-row split">
            <label>
              CodeChef Username
              <input
                value={codechef}
                onChange={(event) => setCodechef(event.target.value)}
                placeholder="CodeChef Handle"
              />
            </label>
            <label>
              GeeksforGeeks Username
              <input
                value={gfg}
                onChange={(event) => setGfg(event.target.value)}
                placeholder="GeeksforGeeks Handle"
              />
            </label>
          </div>

          <div className="task-panel__header" style={{ marginTop: '1rem' }}>
            <h3>Contest Reminders</h3>
            <p className="muted">Get notified 1 hour before the contest starts.</p>
          </div>

          <div style={{ display: 'grid', gap: '0.8rem', marginTop: '0.5rem' }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={sendEmail}
                onChange={(event) => setSendEmail(event.target.checked)}
                style={{ width: '1.2rem', height: '1.2rem', accentColor: 'var(--accent)' }}
              />
              <span>Agree to send contest reminder via email</span>
            </label>
          </div>

          {!sendEmail && (
            <div className="banner banner-error" style={{ padding: '0.6rem 0.8rem', fontSize: '0.9rem' }}>
              ⚠️ You have opted out of email reminders. You will not receive any notifications.
            </div>
          )}

          <button className="primary-button" type="submit" disabled={saving} style={{ marginTop: '1rem' }}>
            {saving ? 'Saving Settings…' : 'Save Profile & Settings'}
          </button>
        </form>
      )}
    </ModalShell>
  );
}
