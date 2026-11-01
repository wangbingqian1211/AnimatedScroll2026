# Docker + MySQL

画作资料库支持 MySQL 8.4。前端仍通过 FastAPI 读写，页面编辑保存后更新 MySQL 中的项目、人物、来源、关系、事件与审计日志。图片和文献文件继续保存在本机 `data/`，不能仅备份数据库而忽略这些文件。

## 配置和启动

项目根目录的 `.env.mysql` 保存数据库配置，已被 Git 忽略。`.env.mysql.example` 只包含占位示例。数据库使用独立应用账户，后端不使用 root 账户。密码通过 `SQLAlchemy.URL.create` 传递，可包含特殊字符。

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
docker compose --env-file .env.mysql -f compose.mysql.yaml up -d --wait mysql
```

命名数据卷 `animatedscroll2026_mysql_data` 保存 MySQL 数据。端口仅绑定 `127.0.0.1:3307`。首次启动初始化账户；修改环境文件里的密码不会自动修改既有数据卷中的账户密码。

## 首次迁移

停止在旧页面编辑后运行：

```powershell
.\.venv\Scripts\python.exe -m scripts.migrate_sqlite_to_mysql
```

迁移工具先使用 SQLite backup API 创建一致性快照，再在单个 MySQL 事务中复制原项目、全部版本日志与任务，并重建五张结构化查询表。它逐项比较原始行内容及查询表数量，校验不通过将回滚。目标数据库非空时拒绝迁移，不清空或覆盖已有内容。源 SQLite 不删除、不修改。

迁移报告在 `data/mysql-migration-时间.json`；SQLite 快照在 `data/backups/before-mysql-时间.sqlite`。重复核验使用 `--verify-only`；该方式要求目标数据仍与源数据库相同，正常创作后的版本差异不应通过重新迁移来覆盖。

## 启动应用

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8002
```

另一个终端：

```powershell
npm run dev
```

默认配置由 `.env.mysql` 加载；环境变量优先。当 `CREATION_DB_BACKEND=mysql` 时连接失败会报错，不会静默回退到 SQLite。`GET /api/database/status` 返回实际后端和连通性，资料库页面顶部据此显示 MySQL。

MySQL 使用 InnoDB 事务、utf8mb4 和 LONGTEXT。保存时通过 `SELECT ... FOR UPDATE` 锁定当前项目，核对版本后一次性提交快照、日志和结构化表，避免两个创作者覆盖同一个版本。后台任务的更新同样写入 MySQL。旧 SQLite 的隐式 rowid 排序在 MySQL 下分别采用日志时间和任务时间排序。

## 验证

普通测试强制使用临时 SQLite，避免碰到创作者数据库：

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

真实 MySQL 测试创建独立测试项目，并在结束时仅删除自身项目的记录：

```powershell
$env:CREATION_TEST_MYSQL='1'
.\.venv\Scripts\python.exe -m pytest -q tests/test_mysql_live.py
Remove-Item Env:CREATION_TEST_MYSQL
```

真实测试覆盖中文及 emoji、超过 TEXT 容量的原文、重新读取数据库、并发保存冲突、审计和查询表的事务回滚，以及后台任务更新与排序。

## 停止与备份

`docker compose --env-file .env.mysql -f compose.mysql.yaml stop` 停止数据库但保留命名数据卷。备份时保留 MySQL 导出、`data/` 中的图片文献与本机环境配置。不要使用删除数据卷的命令进行普通重启。旧 SQLite 是迁移时的快照；切回它不会包含迁移后新增的 MySQL 修改。

前后端固定使用 5173 和 8002。`vite.config.ts` 中代理固定指向 8002，不再读取 `CREATION_API_URL` 临时变量。Windows 可用 `npm run dev:backend` 启动后端。
