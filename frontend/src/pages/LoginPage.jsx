import { useCallback, useEffect, useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';

import BackendWakeSlider from '../components/BackendWakeSlider';
import { useAuth } from '../context/AuthContext';
import {
  BACKEND_RETRY_INTERVAL_SECONDS,
  BACKEND_RETRY_WINDOW_SECONDS,
  isBackendUnavailableError,
} from '../utils/authRetry';

export default function LoginPage() {
  const navigate = useNavigate();
  const { login, googleAuth } = useAuth();
  const [form, setForm] = useState({ username: '', password: '' });
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [retryState, setRetryState] = useState({ active: false, remainingSeconds: 0, attempts: 0 });

  const queuedFormRef = useRef(null);
  const retryDeadlineRef = useRef(0);
  const nextRetryAttemptRef = useRef(0);
  const retryIntervalRef = useRef(null);
  const isRetryingRef = useRef(false);

  const clearRetryLoop = useCallback(() => {
    if (retryIntervalRef.current) {
      window.clearInterval(retryIntervalRef.current);
      retryIntervalRef.current = null;
    }

    queuedFormRef.current = null;
    retryDeadlineRef.current = 0;
    nextRetryAttemptRef.current = 0;
    isRetryingRef.current = false;
    setRetryState({ active: false, remainingSeconds: 0, attempts: 0 });
  }, []);

  const attemptLogin = useCallback(async (submission) => {
    if (!submission || isRetryingRef.current) {
      return undefined;
    }

    isRetryingRef.current = true;

    try {
      await login(submission);
      clearRetryLoop();
      setError('');
      setNotice('');
      setIsSubmitting(false);
      navigate('/', { replace: true });
      return;
    } catch (requestError) {
      if (isBackendUnavailableError(requestError)) {
        const remainingSeconds = Math.max(0, Math.ceil((retryDeadlineRef.current - Date.now()) / 1000));

        if (remainingSeconds <= 0) {
          clearRetryLoop();
          setNotice('');
          setError('Backend did not wake within 1 minute. Please try again.');
          setIsSubmitting(false);
          return;
        }

        queuedFormRef.current = submission;
        nextRetryAttemptRef.current = Date.now() + BACKEND_RETRY_INTERVAL_SECONDS * 1000;
        setRetryState((current) => ({
          active: true,
          remainingSeconds,
          attempts: current.attempts + 1,
        }));
        setNotice(
          `Backend is waking up. Retrying sign in automatically in ${BACKEND_RETRY_INTERVAL_SECONDS} seconds.`,
        );
        setError('');
        isRetryingRef.current = false;
        return;
      }

      clearRetryLoop();
      setError(requestError.response?.data?.detail || 'Failed to sign in, try again.');
      setNotice('');
      setIsSubmitting(false);
    };
  }, [clearRetryLoop, login, navigate]);

  useEffect(() => {
    if (!retryState.active) {
      return undefined;
    }

    retryIntervalRef.current = window.setInterval(() => {
      const remainingSeconds = Math.max(0, Math.ceil((retryDeadlineRef.current - Date.now()) / 1000));

      setRetryState((current) => (current.active ? { ...current, remainingSeconds } : current));

      if (!queuedFormRef.current || isRetryingRef.current) {
        return;
      }

      if (remainingSeconds <= 0) {
        void attemptLogin(queuedFormRef.current);
        return;
      }

      if (Date.now() >= nextRetryAttemptRef.current) {
        void attemptLogin(queuedFormRef.current);
      }
    }, 1000);

    return () => clearRetryLoop();
  }, [attemptLogin, clearRetryLoop, retryState.active]);

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError('');
    if (isSubmitting) {
      return;
    }

    setIsSubmitting(true);
    setNotice('');
    retryDeadlineRef.current = Date.now() + BACKEND_RETRY_WINDOW_SECONDS * 1000;
    nextRetryAttemptRef.current = Date.now() + BACKEND_RETRY_INTERVAL_SECONDS * 1000;

    await attemptLogin(form);
  };

  const handleGoogleAuthenticate = async (token) => {
    setIsSubmitting(true);
    setError('');
    setNotice('');
    try {
      await googleAuth({ action: 'login', token });
      setError('');
      setIsSubmitting(false);
      navigate('/', { replace: true });
    } catch (requestError) {
      setIsSubmitting(false);
      if (requestError.response?.status === 404) {
        const { email, name } = requestError.response.data || {};
        // Redirection to register with prefilled data
        navigate('/register', {
          state: {
            googleEmail: email,
            googleName: name,
            googleToken: token
          }
        });
      } else {
        setError(requestError.response?.data?.detail || 'Google sign in failed. Please try again.');
      }
    }
  };

  const handleGoogleClick = () => {
    const clientId = process.env.REACT_APP_GOOGLE_CLIENT_ID || '1013850858127-9jplour59oav67p6hnl556psug2puher.apps.googleusercontent.com';
    if (!clientId || clientId === 'YOUR_GOOGLE_CLIENT_ID_HERE') {
      setError('Please configure REACT_APP_GOOGLE_CLIENT_ID in frontend/.env');
      return;
    }

    if (typeof window.google === 'undefined') {
      setError('Google SDK not loaded yet. Please wait or refresh the page.');
      return;
    }

    try {
      setError('');
      const client = window.google.accounts.oauth2.initTokenClient({
        client_id: clientId,
        scope: 'email profile openid',
        callback: async (tokenResponse) => {
          if (tokenResponse && tokenResponse.access_token) {
            await handleGoogleAuthenticate(tokenResponse.access_token);
          }
        },
        error_callback: () => {
          setError('Google Auth popup closed or failed to authorize.');
        }
      });
      client.requestAccessToken();
    } catch (err) {
      setError('Google Sign-In initialization failed.');
    }
  };

  return (
    <div className="auth-screen">
      <div className="auth-info-pane">
        <div className="auth-info-content">
          <svg width="64" height="64" viewBox="0 0 400 400" fill="none" xmlns="http://www.w3.org/2000/svg" style={{ marginBottom: '0.5rem' }}>
            <circle cx="200" cy="200" r="180" fill="#0F172A"/>
            <path d="M200 80 Q160 140 170 200 Q160 260 200 300 Q240 260 230 200 Q240 140 200 80" fill="#F97316"/>
            <path d="M200 100 Q170 150 175 190 Q170 230 200 260 Q230 230 225 190 Q230 150 200 100" fill="#FB923C"/>
            <path d="M165 170 L180 185 L210 150" stroke="#67E8F9" stroke-width="18" stroke-linecap="round" stroke-linejoin="round"/>
            <path d="M175 200 L190 215 L220 180" stroke="#22D3EE" stroke-width="16" stroke-linecap="round" stroke-linejoin="round"/>
            <text x="95" y="255" font-family="monospace" font-size="52" fill="#67E8F9" font-weight="bold">{"{"}</text>
            <text x="255" y="255" font-family="monospace" font-size="52" fill="#67E8F9" font-weight="bold">{"}"}</text>
          </svg>
          <h1>Eyes on Streak</h1>
          <p className="subtitle">Maintain consistency, track stats, and lock in your coding streaks across Codeforces, LeetCode, and more.</p>
          
          <div className="features-list">
            <div className="feature-item">
              <span className="feature-icon">🔥</span>
              <div>
                <h3>Streak Maintaining</h3>
                <p>Track your daily logs and build a visual habit grid that keeps you going.</p>
              </div>
            </div>
            <div className="feature-item">
              <span className="feature-icon">📊</span>
              <div>
                <h3>Coding Profiles Sync</h3>
                <p>Connect your handles and watch your platform submissions sync automatically.</p>
              </div>
            </div>
            <div className="feature-item">
              <span className="feature-icon">🔔</span>
              <div>
                <h3>Smart Reminders</h3>
                <p>Never miss a contest with automated Email alerts.</p>
              </div>
            </div>
          </div>
        </div>
      </div>
      
      <div className="auth-form-pane">
        <div className="auth-card">
          <p className="eyebrow">Streak Tracker</p>
          <h1>Welcome Back</h1>
          
          <BackendWakeSlider
            active={retryState.active}
            title="Keep the form open while the backend wakes"
            message="Your sign-in request is queued locally and will keep retrying automatically for up to one minute."
            remainingSeconds={retryState.remainingSeconds}
            totalSeconds={BACKEND_RETRY_WINDOW_SECONDS}
            attemptLabel={`Attempt ${retryState.attempts + 1}`}
          />
          
          {notice && !retryState.active ? <div className="banner banner--notice">{notice}</div> : null}
          {error ? <div className="banner banner--error">{error}</div> : null}
          
          <form className="stack-form" onSubmit={handleSubmit}>
            <input
              value={form.username}
              disabled={isSubmitting}
              onChange={(event) => setForm((current) => ({ ...current, username: event.target.value }))}
              placeholder="Username"
            />
            <input
              type="password"
              value={form.password}
              disabled={isSubmitting}
              onChange={(event) => setForm((current) => ({ ...current, password: event.target.value }))}
              placeholder="Password"
            />
            <button type="submit" className="primary-button" disabled={isSubmitting}>
              {isSubmitting ? 'Logging in...' : 'Log in'}
            </button>
          </form>

          <div className="social-login-divider">
            <span>or sign in with</span>
          </div>

          <button 
            type="button" 
            className="google-login-btn" 
            disabled={isSubmitting}
            onClick={handleGoogleClick}
          >
            <svg className="google-icon-svg" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
              <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4" />
              <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853" />
              <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z" fill="#FBBC05" />
              <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z" fill="#EA4335" />
            </svg>
            Google
          </button>

          <p className="auth-card__footer">
            New to Streak Tracker? <Link to="/register">Sign up</Link>
          </p>
        </div>
      </div>
    </div>
  );
}