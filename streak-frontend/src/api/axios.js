import axios from 'axios';

export const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://127.0.0.1:8000/api';

const accessTokenKey = 'streak_access_token';
const refreshTokenKey = 'streak_refresh_token';
const userKey = 'streak_user';

export function getStoredUser() {
  const rawUser = localStorage.getItem(userKey);

  if (!rawUser) {
    return null;
  }

  try {
    return JSON.parse(rawUser);
  } catch {
    return null;
  }
}

export function setStoredAuth({ access, refresh, user }) {
  if (access) {
    localStorage.setItem(accessTokenKey, access);
  }

  if (refresh) {
    localStorage.setItem(refreshTokenKey, refresh);
  }

  if (user) {
    localStorage.setItem(userKey, JSON.stringify(user));
  }
}

export function clearStoredAuth() {
  localStorage.removeItem(accessTokenKey);
  localStorage.removeItem(refreshTokenKey);
  localStorage.removeItem(userKey);
}

export function getStoredAccessToken() {
  return localStorage.getItem(accessTokenKey);
}

export const api = axios.create({
  baseURL: API_BASE_URL,
});

const refreshClient = axios.create({
  baseURL: API_BASE_URL,
});

api.interceptors.request.use((config) => {
  const accessToken = localStorage.getItem(accessTokenKey);

  if (accessToken) {
    config.headers = config.headers || {};
    config.headers.Authorization = `Bearer ${accessToken}`;
  }

  return config;
});

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    const statusCode = error.response?.status;
    const requestUrl = originalRequest?.url || '';

    if (
      statusCode === 401 &&
      originalRequest &&
      !originalRequest._retry &&
      !requestUrl.includes('/auth/login/') &&
      !requestUrl.includes('/auth/register/') &&
      !requestUrl.includes('/auth/refresh/')
    ) {
      originalRequest._retry = true;
      const refreshToken = localStorage.getItem(refreshTokenKey);

      if (refreshToken) {
        try {
          const { data } = await refreshClient.post('/auth/refresh/', { refresh: refreshToken });

          if (data.access) {
            localStorage.setItem(accessTokenKey, data.access);
          }

          if (data.refresh) {
            localStorage.setItem(refreshTokenKey, data.refresh);
          }

          originalRequest.headers = originalRequest.headers || {};
          originalRequest.headers.Authorization = `Bearer ${data.access}`;
          return api(originalRequest);
        } catch {
          clearStoredAuth();
        }
      } else {
        clearStoredAuth();
      }

      if (typeof window !== 'undefined' && window.location.pathname !== '/login') {
        window.location.assign('/login');
      }
    }

    return Promise.reject(error);
  },
);

export { accessTokenKey, refreshTokenKey, userKey };