import { http } from './client';
import type { EpisodeBrief, EpisodeDetail, Paginated } from '../types/models';

export interface EpisodeQuery {
  feed?: string;
  status?: string;
  ingest_state?: string;
  q?: string;
  page?: number;
  size?: number;
}

export const episodeApi = {
  list: (query: EpisodeQuery = {}) => {
    const params = new URLSearchParams();
    Object.entries(query).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') params.set(key, String(value));
    });
    const suffix = params.toString() ? `?${params.toString()}` : '';
    return http.get<Paginated<EpisodeBrief>>(`/episodes${suffix}`);
  },
  detail: (code: string) => http.get<EpisodeDetail>(`/episodes/${code}`),
  reparse: (code: string) =>
    http.post<{
      episode_code: string;
      entries: number;
      unparsed: number;
      ambiguous: number;
      rule_usage: Record<string, number>;
      about_minutes: { raw: string; seconds: number }[];
      open_issues: number;
    }>(`/episodes/${code}/reparse`),
  normalize: (code: string) =>
    http.post<{
      episode_code: string;
      reordered: number;
      merged: number;
      folded: number;
      deleted_rows: number;
      gaps: { issue_key: string; gap_seconds: number }[];
      open_issues: number;
      chapters: EpisodeDetail['chapters'];
    }>(`/episodes/${code}/normalize`),
  addChapter: (code: string, payload: { start_seconds?: number; raw_text?: string; title?: string }) =>
    http.post<{ result: { chapter_id: number }; episode: EpisodeDetail }>(`/episodes/${code}/chapters`, payload),
  patchChapter: (
    code: string,
    chapterId: number,
    payload: { start_seconds?: number; raw_text?: string; title?: string },
  ) =>
    http.patch<{ result: { chapter_id: number }; episode: EpisodeDetail }>(
      `/episodes/${code}/chapters/${chapterId}`,
      payload,
    ),
  deleteChapter: (code: string, chapterId: number) =>
    http.del<{ result: { deleted: number }; episode: EpisodeDetail }>(
      `/episodes/${code}/chapters/${chapterId}`,
    ),
};
