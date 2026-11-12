import { http } from './client';
import type { TaskItem } from '../types/models';

export const taskApi = {
  list: (limit = 30) => http.get<{ items: TaskItem[] }>(`/tasks?limit=${limit}`),
  detail: (code: string) => http.get<{ task: TaskItem }>(`/tasks/${code}`),
  run: (mode: 'ingest' | 'parse' | 'both', feedCodes?: string[]) =>
    http.post<{ task: TaskItem }>('/tasks/run', { mode, feed_codes: feedCodes ?? null }),
};
