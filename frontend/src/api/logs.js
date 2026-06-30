import { api } from './axios';

export async function getTodayLog() {
  const response = await api.get('/logs/today/');
  return response.data;
}

export async function updateTodayLog(completedTaskIds, journalEntry, isFrozen) {
  const payload = { completed_task_ids: completedTaskIds };
  if (journalEntry !== undefined) payload.journal_entry = journalEntry;
  if (isFrozen !== undefined) payload.is_frozen = isFrozen;

  const response = await api.patch('/logs/today/', payload);
  return response.data;
}

export async function getHistory() {
  const response = await api.get('/logs/history/');
  return response.data;
}

export async function getLogByDate(date) {
  const response = await api.get(`/logs/${date}/`);
  return response.data;
}

export async function updateLogByDate(date, completedTaskIds, journalEntry, isFrozen) {
  const payload = {};
  if (completedTaskIds !== undefined) payload.completed_task_ids = completedTaskIds;
  if (journalEntry !== undefined) payload.journal_entry = journalEntry;
  if (isFrozen !== undefined) payload.is_frozen = isFrozen;

  const response = await api.patch(`/logs/${date}/`, payload);
  return response.data;
}