# DeepCareer 项目事实

## 仓库与部署

- GitHub 远程: `napstablook666/DeepCareer`（fork 自 `Zijie933/DeepCareer`）
- 认证: 系统环境变量 `GH_TOKEN` / `GITHUB_TOKEN`（用户级），`gh` CLI 已登录

## 技术栈

- 后端: Python 3.11+, FastAPI 0.109+, SQLAlchemy async, Pydantic
- 前端: React 18, Vite, TailwindCSS, Ant Design, Axios
- 数据库: PostgreSQL 17 + pgvector 0.2.4
- 缓存: Redis 7（可选）
- 爬虫: Playwright + BeautifulSoup4
- Embedding/Rerank: bge-m3 + bge-reranker-v2-m3（模力方舟/Gitee AI 免费接口）

## 核心模块

| 模块 | 路径 |
|------|------|
| 智能匹配（5 维评分） | `backend/services/matcher_service.py` |
| 简历提取（规则+LLM） | `backend/services/extractor_service.py` |
| Embedding 服务 | `backend/utils/embedding_service.py` |
| BOSS 直聘爬虫 | `backend/crawlers/boss_web_crawler_playwright.py` |
| CLI 入口 | `backend/cli.py` |
| API 路由 | `backend/api/` |

## 匹配权重（可配置）

职位方向 0.30 | 技能 0.25 | 经验 0.20 | 学历 0.15 | 语义 0.10