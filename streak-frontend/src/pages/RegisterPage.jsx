import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';

import { useAuth } from '../context/AuthContext';

const WAIT_SECONDS = 60;

function formatCountdown(seconds) {
  const minutes = String(Math.floor(seconds / 60)).padStart(2, '0');
  const remainingSeconds = String(seconds % 60).padStart(2, '0');

  return `${minutes}:${remainingSeconds}`;
}

export default function RegisterPage() {
  const navigate = useNavigate();
  const { register } = useAuth();
  const [form, setForm] = useState({ username: '', email: '', password: '' });
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [countdown, setCountdown] = useState(0);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [queuedForm, setQueuedForm] = useState(null);

  useEffect(() => {
    if (countdown <= 0) {
      return undefined;
    }

    const timer = setTimeout(() => {
      setCountdown((currentCountdown) => Math.max(currentCountdown - 1, 0));
    }, 1000);

    return () => clearTimeout(timer);
  }, [countdown]);

  useEffect(() => {
    if (countdown !== 0 || !queuedForm || isSubmitting) {
      return;
    }

    const submitAfterWait = async () => {
      const submission = queuedForm;
      setQueuedForm(null);
      setNotice('Creating account...');
      setIsSubmitting(true);

      try {
        await register(submission);
        navigate('/', { replace: true });
      } catch (requestError) {
        setError(requestError.response?.data?.detail || 'Failed to save, try again.');
        setNotice('');
      } finally {
        setIsSubmitting(false);
      }
    };

    submitAfterWait();
  }, [countdown, isSubmitting, navigate, queuedForm, register]);

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError('');
    if (countdown > 0 || isSubmitting) {
      return;
    }

    setNotice('Please wait while Render wakes the backend. Retrying automatically.');
    setQueuedForm(form);
    setCountdown(WAIT_SECONDS);
  };

  return (
    <div className="auth-screen">
      <div className="auth-card">
        <p className="eyebrow">Streak Tracker</p>
        <h1>Create account</h1>
        {notice ? <div className="banner banner--notice">{notice}{countdown > 0 ? ` ${formatCountdown(countdown)} remaining.` : ''}</div> : null}
        {error ? <div className="banner banner--error">{error}</div> : null}
        <form className="stack-form" onSubmit={handleSubmit}>
          <input
            value={form.username}
            disabled={countdown > 0 || isSubmitting}
            onChange={(event) => setForm((current) => ({ ...current, username: event.target.value }))}
            placeholder="Username"
          />
          <input
            type="email"
            value={form.email}
            disabled={countdown > 0 || isSubmitting}
            onChange={(event) => setForm((current) => ({ ...current, email: event.target.value }))}
            placeholder="Email"
          />
          <input
            type="password"
            value={form.password}
            disabled={countdown > 0 || isSubmitting}
            onChange={(event) => setForm((current) => ({ ...current, password: event.target.value }))}
            placeholder="Password"
          />
          <button type="submit" className="primary-button" disabled={countdown > 0 || isSubmitting}>
            {countdown > 0 ? `Wait ${formatCountdown(countdown)}` : isSubmitting ? 'Creating...' : 'Create account'}
          </button>
        </form>
        <p className="auth-card__footer">
          Already have an account? <Link to="/login">Login</Link>
        </p>
      </div>
    </div>
  );
}