# migrations

演示项目使用 **SQLAlchemy 2.0 `Base.metadata.create_all`** 在 backend 启动时建表
（`src/config/app.py::_bootstrap_database`），这样 `docker compose up` 不需要额外的迁移步骤。

`0001_initial.sql` 是同一份结构的可审阅 DDL（MySQL 8.0），用途：

- 给 DBA 在正式环境先建表，再让应用连上去；
- 评审时快速核对表结构、索引与外键。

结构变更约定：

1. 改 `src/models/*.py`；
2. 同步改本目录新增 `000N_*.sql`（只增不改历史文件）；
3. 若已有环境需要在线变更，单独写 migration 并在 README 记录。
