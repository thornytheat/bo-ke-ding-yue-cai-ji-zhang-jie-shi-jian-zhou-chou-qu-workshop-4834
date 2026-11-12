# podcastdig · 播客订阅采集与章节时间轴抽取工坊

> 把 RSS / 平台接口 / 目录页里的播客 show notes，抽取成剪辑师能直接切的时间轴：时间码解析 + 章节窗口不变量校验 + 异常队列 + 剪辑清单导出。

- 批次：`batch-20261112b` ｜ 编号：`gb-579` ｜ 短名：`podcastdig`
- 端口：前端 `18252` / 后端 `19252` / MySQL `17752`
- 技术栈：React 18 + TypeScript + Vite / FastAPI + SQLAlchemy 2.0 + Celery / MySQL 8.0 / Redis 7 / Nginx

---

## 1. 真实场景（不是演示 CRUD）

**模拟客户**：声景内容工作室 · 节目运营组（6 人），运营 9 档中文播客（商业访谈、城市漫游、科技周报），本期接入其中 6 个订阅源。

**现在怎么做**：运营每周从 RSS、小宇宙式平台页、Apple 式目录（本仓库是三份**确定性夹具**：RSS XML / 平台 JSON / 目录 HTML）拉新单集，人工把 show notes 里的章节时间戳抄进剪辑表，剪辑师按表切片；漏抄就整集重听。

**三个痛点**

1. 时间戳格式混乱：`01:23:45` / `12:30` / `@12:30` / `1时02分30秒` / `45分30秒` / `约 12 分钟处`，还有 `1h02m` 这种根本认不出来的写法；
2. 章节缺失或乱序，重叠、过短、缺口没人管，剪辑切错；
3. 平台静默改简介 / 补链接，没人追踪 diff，漏更快讯。

**上下游**

- 上游：3 类订阅源（RSS 2.0 + itunes、平台 JSON、目录 HTML），共 6 个源 / 48 集；
- 本系统替代：「人工抄时间戳 + Excel 排序 + 拍脑袋判断章节是否可用」；
- 下游：剪辑师的**切片清单 CSV**、发布排期，以及内容运营的周度异常复盘。

**一天的工作剧本（演示数据与剧本一致）**

1. 09:00 运营主管在「订阅源」点「抓取预览」，看到 `techweekly` 有 1 集平台简介被改写；
2. 09:02 运行批次（采集）：扫描 48 集，**新增 3**（水位线后新到达、尚未入库）、**更新 5**（平台改写简介）、不变 40；
3. 09:04 运行批次（解析）：260 行章节、**4 行时间码未识别**、不变量校验出 **22 条异常**（乱序 12 / 重叠 3 / 缺口 3 / 未识别 4）；
4. 09:06 内容运营打开 `EP-044 城市漫游 · 泉州`，重跑解析 → 「约 12 分钟处」落到 **720s**；
5. 09:07 点「应用不变量修正」：3 条乱序重排、1 条重叠合并、0 条过短折叠，该集异常清零；
6. 09:10 到「异常队列」复核剩余 18 条，处置 2 条缺口告警并写明依据；
7. 09:15 导出**剪辑清单 CSV（48 行，含起止秒与时长）**发给剪辑师；
8. 剪辑师用只读账号登录，只能看节目库 / 章节时间轴 / 导出清单，改章节返回 403。

## 2. 主要功能

| 模块 | 页面 | 做什么 |
|---|---|---|
| 配置 | `/feeds` | 6 个订阅源的频率 / 主播 / 启停；抓取预览（只读夹具 + 内容指纹 diff，不落库） |
| 运行 | `/feeds` | 采集 / 解析 / 采集+解析 三种批次，投递 Celery worker，前端轮询批次状态与日志 |
| 解析计算 | 后端 `parse_service` / `validation_service` | 时间戳正则族解析 + 章节窗口不变量校验（见 §5） |
| 复核归因 | `/issues`、`/episodes/:code` | 22 条异常工单按类型归因、给出修正建议、内联编辑章节、一键应用不变量修正 |
| 导出 | `/issues` | 剪辑清单 CSV（每集一行）、章节切点 CSV（每章一行）、异常清单 CSV |
| 看板 | `/library` | 节目库：时长、章节数、解析状态、异常数、未识别数；筛选 / 搜索 / 分页 |

## 3. 演示账号

密码统一 `Demo@2026`，域名 `podcastdig.io`。

| 邮箱 | 角色 | 权限 | 典型动作 |
|---|---|---|---|
| `admin@podcastdig.io` | 运营主管 | 全部（含 feed:write、audit:read） | 维护订阅源、跑批次、处置异常、导出、看审计 |
| `analyst@podcastdig.io` | 内容运营 | task:run / chapter:write / issue:resolve / export:read | 跑采集解析、修章节、处置异常、导出 |
| `viewer@podcastdig.io` | 剪辑师（只读） | library:read / export:read | 看节目库与时间轴、导出剪辑清单；改章节/跑批次返回 403 |

权限判定在服务端（`src/middlewares/rbac.py` + 路由依赖），前端只是隐藏入口。

## 4. 快速启动

```bash
cd projects/gb-579
cp .env.example .env          # 已带一份可直接用的 .env
docker compose config --quiet
docker compose up -d --build  # 首次构建约 4-6 分钟（pip 清华源 / npm npmmirror）
docker compose ps             # 5/5 healthy
```

- 打开 <http://localhost:18252>
- 后端健康检查：<http://localhost:19252/api/health>
- `SEED_DEMO=true` 时 backend 启动自动跑一次 seed（失败只记日志不阻塞）。

本地开发：

```bash
# backend
cd backend && python -m venv .venv && . .venv/bin/activate
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt
SEED_DEMO=false uvicorn src.main:app --reload --port 8000
# worker
celery -A src.config.celery_app worker -B -l info --concurrency=2
# frontend
cd frontend && npm install && npm run dev   # /api 代理到 19252
```

## 5. 算法口径（后端 Python 真算，前端不硬编码）

### 算法 1：时间戳解析与归一（`backend/src/services/parse_service.py`）

| 规则 | 示例 | 置信度 | 说明 |
|---|---|---|---|
| `hh:mm:ss` | `01:23:45`、`0:08:20` | 0.95 | 时:分:秒 |
| `mm:ss` | `12:30`、`01:00` | 0.86 | 分:秒；**歧义判定**见下 |
| `X时Y分Z秒` | `1时02分30秒`、`0时08分10秒` | 0.90 | 中文时长单位 |
| `X分Y秒` | `45分30秒`、`8分10秒` | 0.90 | 中文分钟单位 |
| `约 N 分钟处` | `约 12 分钟处` | 0.62 | 模糊表述，低置信进人工复核 |
| `@mm:ss` | `@12:30` | 0.88 | 平台锚点写法 |
| 未识别 | `1h02m` | 0.00 | 保留原文，进异常队列，不参与时间轴 |

**歧义规则**：裸 `M:SS` 且 `M < 60`、单集时长 ≥ 60 分钟、`M*3600+SS` 仍落在时长内 → 按 **mm:ss** 解释并标 `ambiguous=true`（`1:11` 在 69 分钟节目里既可能是 1 分 11 秒，也可能是 1 时 11 分）。输出 `seconds`、`raw`、`rule`、`confidence`、`ambiguous`。

### 算法 2：章节窗口不变量校验（`backend/src/services/validation_service.py`）

| # | 不变量 | 判定 | 产出 |
|---|---|---|---|
| 1 | 严格递增 | 按 show notes 行序，时间点 < 前文最大值 | `out_of_order`，建议重排 |
| 2 | 末章 ≤ 时长 | 任一时间点 > 单集时长 | `over_duration` |
| 3 | 重叠合并 | 同一时间点（容差 0s）保留置信高者，标题用 ` / ` 合并 | `overlap` |
| 4 | &lt; 20s 折叠 | 相邻窗口短于 20 秒折叠进前一章 | `too_short` |
| 5 | 缺口 &gt; 8min | 相邻章节空档超过 480 秒，给出建议补章区间 | `gap_warning` |

校验**不改原文**：返回 issues + 一份 `auto_fixed` 的修正章节表；只有人工点「应用不变量修正」才写库（`POST /api/episodes/{code}/normalize`）。

失败态：整集没有可识别时间码 → `failed` 状态 + `unparsed:all` 工单；越界 / 重复时间点写入返回 422 / 409。

## 6. 数据模型（4 个核心实体 + 2 张支撑表）

| 实体 | 表 | 贯穿位置 |
|---|---|---|
| Feed 订阅源 | `feeds` | `models/feed.py` → `schemas/feed.py` → `services/feed_service.py` → `controllers/feed_controller.py` → `routes/feeds.py` → `api/feeds.ts` → `pages/Feeds.tsx` |
| Episode 单集 | `episodes` | `models/episode.py` → `schemas/episode.py` → `services/episode_service.py` → `controllers/episode_controller.py` → `routes/episodes.py` → `api/episodes.ts` → `pages/Library.tsx` / `pages/EpisodeDetail.tsx` |
| Chapter 章节 | `chapters` | `models/chapter.py` → `schemas/episode.py` → `services/chapter_service.py` → `controllers/chapter_controller.py` → `routes/episodes.py` → `api/episodes.ts` → `pages/EpisodeDetail.tsx` |
| DigestTask 采集批次 | `digest_tasks` | `models/digest_task.py` → `schemas/task.py` → `services/task_service.py` / `digest_service.py` → `controllers/task_controller.py` → `routes/tasks.py` → `api/tasks.ts` → `pages/Feeds.tsx` |

支撑表：`chapter_issues`（不变量校验产出的异常工单，可人工处置）、`audit_logs`（审计）、`users`。

## 7. 目录

```
gb-579/
├── docker-compose.yml          # 5 服务：frontend/backend/worker/db/redis
├── .env / .env.example
├── backend/
│   ├── Dockerfile              # python:3.11-slim，健康检查用 urllib（不装 curl）
│   ├── requirements.txt
│   ├── migrations/0001_initial.sql
│   ├── fixtures/               # 6 份确定性订阅源快照（RSS/JSON/HTML）
│   ├── scripts/                # seed_demo / demo_config / build_fixtures / audit_seed_fixture
│   └── src/
│       ├── config/             # settings / database / app / celery_app
│       ├── constants/          # enums（共享枚举唯一定义）/ roles / error_codes / limits
│       ├── models/             # 7 张表
│       ├── schemas/            # 入参校验
│       ├── services/           # parse / validation / digest / fixture / feed / episode / chapter / issue / export / task / summary / audit
│       ├── controllers/        # 8 个 controller
│       ├── routes/             # 9 组路由，统一 /api 前缀
│       ├── middlewares/        # auth(JWT) / rbac / rate_limit / audit_logger / error_handler
│       └── utils/              # security / errors / logger / timecode / timeutil / fingerprint
└── frontend/
    ├── Dockerfile              # node:20-alpine 构建 → nginx:1.27-alpine
    ├── nginx.conf              # /api/ 反代 backend:8000 + SPA 回落
    └── src/
        ├── api/                # client / auth / feeds / episodes / tasks / issues / exports
        ├── stores/             # authStore / uiStore
        ├── types/              # models.ts
        ├── components/common/  # ReelMark / TapeLabel / Timecode / StatusPill / ChapterTimeline / IssueMixBar / PageHead / EmptyState / Toasts
        ├── components/layout/  # AppShell
        ├── hooks/              # useAsync / usePolling
        ├── pages/              # Login / Library / EpisodeDetail / Feeds / Issues
        ├── router/             # 路由 + RequireAuth / RequirePermission
        ├── utils/              # format / errorMessage
        ├── constants/          # enums（前端副本）/ roles / ui
        └── styles/             # tokens.css / global.css
```

## 7.5 技术栈

| 层 | 选型 | 说明 |
|---|---|---|
| 前端 | React 18.3 + TypeScript 5.6 + Vite 5.4 + React Router 6 | 无 UI 框架，样式全手写（`oklch()` 令牌 + 磁带标签视觉） |
| 图表 | 原生 SVG / Canvas 级自绘 | 走带时间轴（DOM + CSS 刻度）、异常构成环图（SVG stroke-dasharray），无图表 CDN |
| 后端 | FastAPI 0.115 + SQLAlchemy 2.0 + Pydantic 2 | 4 层：route → controller → service → model |
| 任务 | Celery 5.4 + Redis 7 | 采集/解析批次投递 worker，失败降级为内联执行 |
| 数据库 | MySQL 8.0（utf8mb4） | SQLAlchemy `create_all` 建表 + `migrations/0001_initial.sql` 可审阅 DDL |
| 鉴权 | PyJWT（HS256）+ bcrypt(passlib) | JWT 中间件解析 + rbac 依赖按角色 403 |
| 网关 | Nginx 1.27 | `/api/` 反代 backend:8000（剥前缀）+ SPA 回落 |
| 基础设施 | Docker Compose，5 服务全部带 healthcheck | 命名卷 `db_data` / `redis_data` / `tape_archive` |

## 8. 环境变量

| 变量 | 默认值 | 说明 |
|---|---|---|
| `COMPOSE_PROJECT_NAME` | `podcastdig` | 容器名前缀 |
| `FRONTEND_PORT` / `BACKEND_PORT` / `DB_PORT` | `18252` / `19252` / `17752` | 宿主端口 |
| `DB_NAME` / `DB_USER` / `DB_PASSWORD` / `DB_ROOT_PASSWORD` | `podcastdig` / … | MySQL 8.0 |
| `JWT_SECRET` | `podcastdig-jwt-secret-change-me-2026` | HS256 签名 |
| `REDIS_URL` | `redis://redis:6379/0` | 限流 + Celery broker |
| `SEED_DEMO` | `true` | 启动自动 seed（幂等） |
| `RATE_LIMIT_PER_MINUTE` / `RATE_LIMIT_WRITE_PER_MINUTE` | `600` / `120` | 读 / 写限流 |
| `FIXTURE_DIR` | `/app/fixtures` | 确定性订阅源快照目录 |
| `EXPORT_DIR` | `/app/var/exports` | 导出留档（命名卷 `tape_archive`） |

## 9. Docker 说明

- 恰好 5 个服务，全部带 `healthcheck`：

| 服务 | 镜像 | 健康检查 |
|---|---|---|
| `db` | `mysql:8.0` | `mysqladmin ping` |
| `redis` | `redis:7-alpine` | `redis-cli ping` |
| `backend` | 自建 `python:3.11-slim` | `urllib` 请求 `/api/health` |
| `worker` | 复用 backend 镜像 | Redis 心跳键 `podcastdig:worker:heartbeat`（beat 每 20s 写）兜底 `celery ping` |
| `frontend` | 自建 `nginx:1.27-alpine` | `wget --spider /` |

- `depends_on` 全部用 `service_healthy`；命名卷 `db_data` / `redis_data` / `tape_archive`（backend 与 worker 共享导出留档）。
- 顶层 `name: podcastdig`，无 `version:`；容器名 `${COMPOSE_PROJECT_NAME:-podcastdig}-<role>`。
- 前端 Nginx：`location /api/ { proxy_pass http://backend:8000/; }` + `try_files ... /index.html`。

## 10. seed 与幂等

`backend/scripts/seed_demo.py`：

- 3 账号 / 6 订阅源 / 48 单集 / **260 章节** / **22 异常工单** / 4 条历史批次；
- 章节与工单**不是手写常量**：seed 调用生产同款 `parse_service` + `validation_service`，所以种子里的数字就是算法跑出来的数字；
- 自然键 upsert：`users.email`、`feeds.code`、`episodes.guid`、`chapters.seed_key`、`chapter_issues.issue_key`、`digest_tasks.code`；
- 重复执行不新增、不覆盖人工修改（章节只在「该集还没有任何章节」时生成；工单只补缺失 key）；
- 结束打印一行（两次运行逐字一致）：

```
SEED_SUMMARY brand=podcastdig feeds=6 episodes=48 chapters=260 issues=22 users=3
```

手动重跑：`docker compose exec backend python -m scripts.seed_demo`

## 11. 共享枚举出现位置

前端副本 `frontend/src/constants/enums.ts`，后端唯一定义 `backend/src/constants/enums.py`。

| 枚举 | 后端 | 前端 | 落库/展示位置 |
|---|---|---|---|
| `Role` | `constants/enums.py` | `constants/enums.ts` + `constants/roles.ts` | `users.role`、JWT payload、`rbac.py`、AppShell 角色展示 |
| `FeedKind` | `constants/enums.py` | `constants/enums.ts` | `feeds.kind`、`fixture_service._READERS`、Feeds 页标签 |
| `IngestState` | `constants/enums.py` | `types/models.ts` | `episodes.ingest_state`、Library「待入库」、采集新增口径 |
| `ParseStatus` | `constants/enums.py` | `constants/enums.ts` | `episodes.parse_status`、Library/详情状态胶囊 |
| `ChapterSource` | `constants/enums.py` | `constants/enums.ts` | `chapters.source`、详情表来源列、`ChapterTimeline` 手动标记 |
| `IssueKind` | `constants/enums.py` | `constants/enums.ts`（含展示顺序） | `chapter_issues.kind`、异常队列筛选、`IssueMixBar` 配色 |
| `IssueStatus` | `constants/enums.py` | `types/models.ts` | `chapter_issues.status`、异常队列状态列 |
| `TaskMode` / `TaskStatus` | `constants/enums.py` | `constants/enums.ts` | `digest_tasks.mode/status`、Feeds 批次账本 |

`constants/roles.py`（权限点）与 `frontend/src/constants/roles.ts` 也是成对维护。

## 12. 已知差异 / 限制（诚实清单）

1. **订阅源是确定性夹具**：`backend/fixtures/` 是静态快照（RSS/JSON/HTML），采集不访问网络，也不做真实反爬/重试退避；`fixtures` 由 `scripts/build_fixtures.py` 从 `demo_config.py` 生成，改数据后需重跑。
2. **字体依赖 Google Fonts**：`Chivo` / `IBM Plex Mono` 走 Google Fonts；离线环境回退到 `PingFang SC / Hiragino Sans GB / 系统等宽`，中文观感与在线略有差异（详见 test-artifacts 的 TESTING）。
3. **「采集新增」的口径**：seed 契约锁定 `episodes=48`，所以「新增 3」指**水位线之后新到达、尚未入库采集**的 3 集（`ingest_state=pending` → 采集时置 `synced`），采集不改变单集总数；「更新 5」是平台改写简介的 5 集。
4. **批次是原子的**：采集先把范围内所有源的夹具读通，任一源断档整批回滚、批次 `failed` 并在 `error_text` 与日志里指出来源（源清单上该源标「最近抓取失败」）；所有源读通后才统一写库、批次结束一次性提交，失败后重试不留半批数据。重复运行同一批不新增、不重复更新（内容指纹比对）；简介（show notes）变化的集在同一批次内重建章节时间轴并刷新异常队列，人工补录章节保持原样。
5. 演示环境用 `Base.metadata.create_all` 建表，`migrations/0001_initial.sql` 只是同结构的可审阅 DDL，没有引入 Alembic。
6. 批次同步执行（单进程 worker，48 集毫秒级完成）；真实场景应改成流式分片 + 失败重试队列。

## License

MIT（演示项目，数据均为虚构）。
