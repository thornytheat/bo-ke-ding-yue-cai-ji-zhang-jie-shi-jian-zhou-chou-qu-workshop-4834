import { http } from './client';
import type { Feed, FeedPreview, Overview } from '../types/models';

export const feedApi = {
  list: () => http.get<{ items: Feed[] }>('/feeds'),
  detail: (code: string) => http.get<{ feed: Feed }>(`/feeds/${code}`),
  preview: (code: string) => http.get<FeedPreview>(`/feeds/${code}/preview`),
  patch: (code: string, payload: { active?: boolean; cadence?: string; host?: string; note?: string }) =>
    http.patch<{ feed: Feed }>(`/feeds/${code}`, payload),
};

export const summaryApi = {
  overview: () => http.get<Overview>('/summary'),
};
