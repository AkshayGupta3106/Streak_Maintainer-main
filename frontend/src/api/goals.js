import { api } from './axios';

export async function getGoals() {
  const response = await api.get('/goals/');
  return response.data;
}

export async function createGoal(payload) {
  const response = await api.post('/goals/', payload);
  return response.data;
}

export async function updateGoal(goalId, payload) {
  const response = await api.patch(`/goals/${goalId}/`, payload);
  return response.data;
}

export async function deleteGoal(goalId) {
  await api.delete(`/goals/${goalId}/`);
}
