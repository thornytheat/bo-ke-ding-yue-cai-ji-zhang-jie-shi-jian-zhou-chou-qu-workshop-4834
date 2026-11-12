import { http } from './client';
import type { IssueItem, IssueSummary, Paginated } from '../types/models';

export interface IssueQuery {
  kind?: string;
  status?: string;
  episode?: string;
  feed?: string;
  page?: number;
  size?: number;
}

export const issueApi = {
  list: (query: IssueQuery = {}) => {
    const params = new URLSearchParams();
    Object.entries(query).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') params.set(key, String(value));
    });
    const suffix = params.toString() ? `?${params.toString()}` : '';
    return http.get<Paginated<IssueItem>>(`/issues${suffix}`);
  },
  summary: () => http.get<IssueSummary>('/issues/summary'),
  resolve: (id: number, note: string) =>
    http.post<{ issue: { id: number; status: string }; summary: IssueSummary }>(`/issues/${id}/resolve`, { note }),
  rescan: () => http.post<{ episodes: number; open: number; resolved: number; total: number }>('/issues/rescan'),
};
