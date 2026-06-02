import { api } from './axios';

export async function getTodayLog() {
  const response = await api.get('/logs/today/');
  return response.data;
}

export async function updateTodayLog(completedTaskIds) {
  const response = await api.patch('/logs/today/', {
    completed_task_ids: completedTaskIds,
  });
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

export async function updateLogByDate(date, completedTaskIds) {
  const response = await api.patch(`/logs/${date}/`, {
    completed_task_ids: completedTaskIds,
  });
  return response.data;
}