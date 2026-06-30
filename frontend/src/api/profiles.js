import { api } from './axios';

export async function getCodingProfile() {
  const response = await api.get('/profile/coding/');
  return response.data;
}

export async function updateCodingProfile(data) {
  const response = await api.patch('/profile/coding/', data);
  return response.data;
}

export async function getUpcomingContests() {
  const response = await api.get('/contests/');
  return response.data;
}

export async function getCodingProfileStats() {
  const response = await api.get('/profile/coding/stats/');
  return response.data;
}

export async function getDailyQuote() {
  const response = await api.get('/quote/');
  return response.data;
}

