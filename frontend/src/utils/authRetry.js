export const BACKEND_RETRY_WINDOW_SECONDS = 60;
export const BACKEND_RETRY_INTERVAL_SECONDS = 5;

export function formatCountdown(seconds) {
  const safeSeconds = Math.max(0, seconds);
  const minutes = String(Math.floor(safeSeconds / 60)).padStart(2, '0');
  const remainingSeconds = String(safeSeconds % 60).padStart(2, '0');

  return `${minutes}:${remainingSeconds}`;
}

export function isBackendUnavailableError(error) {
  return !error.response || error.code === 'ERR_NETWORK' || error.code === 'ECONNABORTED';
}