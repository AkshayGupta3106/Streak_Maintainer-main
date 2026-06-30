import { api } from './axios';

export async function getTasks() {
  const response = await api.get('/tasks/');
  return response.data;
}

export async function createTask(payload) {
  const response = await api.post('/tasks/', payload);
  return response.data;
}

export async function updateTask(taskId, payload) {
  const response = await api.patch(`/tasks/${taskId}/`, payload);
  return response.data;
}

export async function deleteTask(taskId) {
  await api.delete(`/tasks/${taskId}/`);
}