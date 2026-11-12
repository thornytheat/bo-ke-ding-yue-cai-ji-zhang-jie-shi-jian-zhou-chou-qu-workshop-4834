import { downloadCsv } from './client';

export const exportApi = {
  clipList: () => downloadCsv('/exports/clip-list.csv', 'podcastdig-clip-list.csv'),
  chapterCuts: () => downloadCsv('/exports/chapter-cuts.csv', 'podcastdig-chapter-cuts.csv'),
  issues: () => downloadCsv('/exports/issues.csv', 'podcastdig-issues.csv'),
};
