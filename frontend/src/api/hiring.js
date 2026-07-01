import { api } from './axios';

export async function getHiringDashboard() {
  const response = await api.get('/hiring/dashboard/');
  return response.data;
}

export async function getHiringAnalytics() {
  const response = await api.get('/hiring/analytics/');
  return response.data;
}

export async function getHiringTimeline() {
  const response = await api.get('/hiring/timeline/');
  return response.data;
}

export async function getCalendarEvents(year, month) {
  const response = await api.get('/hiring/calendar/events/', {
    params: { year, month }
  });
  return response.data;
}

export async function triggerScrape(sources = []) {
  const response = await api.post('/hiring/scrape/', { sources });
  return response.data;
}

export async function getCompanies() {
  const response = await api.get('/hiring/companies/');
  return response.data;
}

export async function getSeasons() {
  const response = await api.get('/hiring/seasons/');
  return response.data;
}

export async function createOpportunity(payload) {
  const response = await api.post('/hiring/opportunities/', payload);
  return response.data;
}

export async function updateOpportunity(oppId, payload) {
  const response = await api.patch(`/hiring/opportunities/${oppId}/`, payload);
  return response.data;
}

export async function deleteOpportunity(oppId) {
  await api.delete(`/hiring/opportunities/${oppId}/`);
}
