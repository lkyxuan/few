# Repository Guidelines

> 本文为精简贡献指引；更完整的运维与架构细节请参见 `CLAUDE.md`（位于仓库根目录）。该文件包含虚拟环境、SystemD、网络代理、数据库与常见故障的权威说明。

## 项目结构与模块组织
- `datasync/` Python 数据同步服务（`src/`、`config/`、`sql/`、`systemd/`）。
- `datainsight/` 指标计算引擎（`src/`、`config/`）— 生产就绪。
- `monitor/` 监控服务（FastAPI，含 `src/`、`config/`、`requirements.txt`）。
- `dataview/` 前端 Next.js（`frontend/`）与后端 FastAPI（`backend/`）。
- 共享与文档：`shared/`、`data/`、`docs/`、`scripts/`。

## 构建、测试与开发命令
- DataSync：`cd datasync && python3 -m venv venv && . venv/bin/activate && pip install -r requirements.txt`。
  - 运行：`python src/main.py status|sync|cleanup|migrate|health`。
  - 测试：`pytest -q` 或 `pytest --cov=datasync/src`。
- DataInsight：`cd datainsight && . venv/bin/activate`（创建/复用 venv），`python src/main.py run|daemon|status -c config/datainsight.yml`。
- Monitor：`cd monitor && python3 -m venv venv && . venv/bin/activate && pip install -r requirements.txt && python src/main.py`。
- DataView 前端：`cd dataview/frontend && npm run dev|build|lint`。
- DataView 后端：`cd dataview/backend && python3 -m venv venv && . venv/bin/activate && pip install -r requirements.txt && python run.py`。

## 编码风格与命名约定
- Python：4 空格缩进；模块/函数用 `snake_case`，类用 `PascalCase`，补充类型注解。
  - 工具：`datasync` 中使用 `black .`、`flake8`（提交前确保通过）。
- TypeScript/React：遵循 Next.js 约定；`npm run lint`（ESLint）；页面/路由置于 `src/app/...`。
- 文件命名：语义清晰，例如 `core/sync_manager.py`、`api/monitor_api.py`。

## 测试规范
- 统一使用 `pytest`；测试放在 `<module>/tests/`，文件名 `test_*.py`。
- 重点路径需有覆盖；推荐 `pytest --cov` 输出覆盖率。
- API（monitor/dataview-backend）：使用 FastAPI TestClient 覆盖路由与健康检查。

## 提交与 Pull Request 规范
- 使用 Conventional Commits：`feat:`、`fix:`、`refactor:`、`docs:`、`chore:`（中英皆可）。
- PR 必须包含：变更说明、关联 issue（如 `Closes #123`）、影响模块、测试证据；UI 变更附截图。
- 要求：构建通过、lint 通过；命令/路径变化需同步更新文档与配置。

## 安全与配置提示
- 禁止提交密钥；`.env*` 仅本地保存（示例：`LOCAL_DB_USER`、`LOCAL_DB_PASSWORD`）。
- 关键配置：`datasync/config/datasync.yml`、`datainsight/config/datainsight.yml`、`monitor/config/*.yml`。
- 日志/生成物体量大，勿入库；遵守 `.gitignore`。

## Agent 协作说明
- 变更尽量最小化、模块内闭环，勿改无关部分。
- 新增命令/端点后，请更新 `docs/` 与本文件。
- 倡导使用 `rg` 快速检索，小而清晰的 diff；勿添加版权头。
