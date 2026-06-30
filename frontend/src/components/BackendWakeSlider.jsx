import { formatCountdown } from '../utils/authRetry';

export default function BackendWakeSlider({ active, title, message, remainingSeconds, totalSeconds, attemptLabel }) {
  if (!active) {
    return null;
  }

  const progress = totalSeconds > 0 ? Math.min(100, Math.max(0, Math.round(((totalSeconds - remainingSeconds) / totalSeconds) * 100))) : 0;

  return (
    <div className="backend-wake-panel" aria-live="polite">
      <div className="backend-wake-panel__header">
        <span className="backend-wake-panel__eyebrow">Render wake-up</span>
        <strong>{title}</strong>
      </div>
      <p>{message}</p>
      <input
        className="backend-wake-slider"
        type="range"
        min="0"
        max="100"
        value={progress}
        readOnly
        aria-label="Backend retry progress"
      />
      <div className="backend-wake-panel__meta">
        <span>{formatCountdown(remainingSeconds)} remaining</span>
        <span>{attemptLabel}</span>
      </div>
    </div>
  );
}