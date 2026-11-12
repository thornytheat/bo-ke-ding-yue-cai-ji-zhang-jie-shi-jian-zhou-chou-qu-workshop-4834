export const NAV_ITEMS = [
  { to: '/library', label: '节目库', sub: '单集 / 章节', permission: 'library:read', reel: 'A' },
  { to: '/feeds', label: '订阅源', sub: '采集 / 解析', permission: 'library:read', reel: 'B' },
  { to: '/issues', label: '异常队列', sub: '校验 / 导出', permission: 'library:read', reel: 'C' },
];

export const STUDIO = '声景内容工作室';

export const LIBRARY_HINT =
  '节目库按发布时间倒序排；点开一集可以对照 show notes 原文核对每个时间码是怎么被识别出来的。';

export const ISSUES_HINT =
  '异常队列来自章节窗口不变量校验：乱序、重叠、超时长、过短折叠、缺口 > 8 分钟、时间码未识别。';

export const FEEDS_HINT =
  '订阅源是三份确定性夹具（RSS XML / 平台 JSON / 目录 HTML）；「抓取预览」只读夹具、不落库，能看到会新增/更新哪些单集。';

export const GAP_THRESHOLD_SECONDS = 8 * 60;
export const SHORT_CHAPTER_SECONDS = 20;

export const DEMO_ACCOUNTS = [
  { email: 'admin@podcastdig.io', role: '运营主管', note: '源 / 规则 / 导出 / 审计' },
  { email: 'analyst@podcastdig.io', role: '内容运营', note: '采集 / 修章节 / 处置异常' },
  { email: 'viewer@podcastdig.io', role: '剪辑师', note: '只读清单与导出' },
];

export const DEMO_PASSWORD = 'Demo@2026';
