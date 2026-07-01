import { api } from './axios';

export async function getQuestions(category = '', difficulty = '') {
  const params = {};
  if (category) params.category = category;
  if (difficulty) params.difficulty = difficulty;
  const { data } = await api.get('/questions/', { params });
  return data;
}

export async function getTodayQuestions() {
  const { data } = await api.get('/questions/today/');
  return data;
}

export async function rateQuestion(questionId, rating) {
  const { data } = await api.post(`/questions/${questionId}/rate/`, { rating });
  return data;
}
