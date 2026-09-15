<p align="center">
  <img src="assets/logo.svg" alt="DeepCareer Logo" width="120" height="120">
</p>

<h1 align="center">DeepCareer</h1>

<p align="center">AI 驱动的智能职位推荐与简历分析系统。</p>

<p align="center">
  <a href="./README.md">English</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11%2B-3776AB?style=flat-square" alt="Python 3.11+">
  <img src="https://img.shields.io/badge/FastAPI-0.109%2B-009688?style=flat-square" alt="FastAPI 0.109+">
  <img src="https://img.shields.io/badge/PostgreSQL-17%2B-4169E1?style=flat-square" alt="PostgreSQL 17+">
  <img src="https://img.shields.io/badge/pgvector-0.2.4-blue?style=flat-square" alt="pgvector">
  <img src="https://img.shields.io/badge/React-18%2B-61DAFB?style=flat-square" alt="React 18+">
  <img src="https://img.shields.io/badge/License-MIT-22C55E?style=flat-square" alt="License MIT">
</p>

基于多维度匹配算法、向量语义搜索和实时爬虫的一站式求职解决方案，帮助你更快找到合适的工作。

## 亮点

| 亮点 | 说明 |
|------|------|
| 智能简历解析 | 支持 PDF、DOCX、图片格式，规则提取（免费快速）+ LLM 提取（高精度）双模式 |
| 多维度职位匹配 | 职位方向、技能、经验、学历、语义相似度 5 维评分，权重可配置 |
| 实时职位爬取 | 基于 Playwright 的浏览器自动化爬虫，支持 Cookie 认证、随机 UA、智能延迟 |
| 流式匹配响应 | SSE（Server-Sent Events）实时推送，边爬边匹配，无需等待全量完成 |
| 向量搜索与重排 | 使用 bge-m3 向量模型 + bge-reranker-v2-m3 重排模型，通过模力方舟（Gitee AI）免费接口调用 |
| 双模式提取 | 规则提取速度快、零成本；LLM 提取精度高，适合复杂简历 |

## 系统架构

```text
┌──────────────────────────────────────────────────────────────────┐
│                         客户端层                                  │
│  ┌──────────────────┐          ┌──────────────────────────────┐  │
│  │  React + Vite    │          │  CLI（deepcareer 命令）      │  │
│  │  （Web 界面）    │          │  (crawl / serve / dev)       │  │
│  └────────┬─────────┘          └──────────────┬───────────────┘  │
└───────────┼────────────────────────────────────┼──────────────────┘
            │ HTTP / SSE                         │
            ▼                                     ▼
┌──────────────────────────────────────────────────────────────────┐
│                      API 层（FastAPI）                            │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────┐  │
│  │ 简历     │ │ 职位     │ │ 智能匹配  │ │ 爬虫     │ │ 健康  │  │
│  │ API      │ │ API      │ │ API      │ │ API      │ │ 检查  │  │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └───────┘  │
└──────────────────────────────────────────────────────────────────┘
            │
            ▼
┌──────────────────────────────────────────────────────────────────┐
│                        服务层                                     │
│  ┌────────────────┐ ┌────────────────┐ ┌──────────────────────┐  │
│  │  提取服务      │ │  匹配服务      │ │  Embedding / Rerank  │  │
│  │  (规则+LLM)    │ │  (5 维评分)    │ │  (bge-m3 / reranker) │  │
│  └────────────────┘ └────────────────┘ └──────────────────────┘  │
│  ┌────────────────┐ ┌────────────────┐                          │
│  │  Playwright    │ │  缓存服务      │                          │
│  │  爬虫          │ │  (Redis，可选)  │                          │
│  └────────────────┘ └────────────────┘                          │
└──────────────────────────────────────────────────────────────────┘
            │                        │
            ▼                        ▼
┌────────────────────┐   ┌────────────────────┐
│   PostgreSQL 17    │   │  Redis 7（可选）    │
│   + pgvector       │   │  （缓存）           │
└────────────────────┘   └────────────────────┘
            │
            ▼
┌──────────────────────────────────────────────────────────────────┐
│                       外部 API                                   │
│  ┌─────────────────────┐  ┌──────────────────────────────────┐   │
│  │  OpenAI 兼容 LLM    │  │  模力方舟 / Gitee AI             │   │
│  │  （可选）           │  │  （免费 bge-m3 + reranker）       │   │
│  └─────────────────────┘  └──────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────┘
```

## 使用示例

### CLI: 终端中爬取与匹配

```bash
# 安装命令行工具
pip install -e .

# 从 BOSS 直聘爬取职位
deepcareer crawl -c "深圳" -k "Python" -n 20

# 启动 API 服务
deepcareer serve -p 8001

# 列出支持的城市
deepcareer cities
```

### API: SSE 流式智能匹配

```bash
POST /api/v2/smart-match/stream
Content-Type: application/json

{
  "resume_id": "abc123",
  "max_jobs": 10
}
```

响应为 Server-Sent Events 流，每个事件携带部分匹配结果（开始、进度、完成或错误）。客户端可以逐条接收结果，无需等待全量处理完毕。

### Web 界面

前后端都启动后，访问 `http://localhost:3000`，可以通过图形界面上传简历、浏览职位、触发智能匹配。

## 快速安装

### 环境要求

| 依赖 | 版本 | 说明 |
|------|------|------|
| Python | 3.11+ | 推荐 3.11.x |
| Node.js | 18+ | 建议使用 LTS 版本 |
| PostgreSQL | 17+ | 需要 pgvector 扩展 |
| Redis | 7+ | 可选，用于缓存 |

### Docker 一键部署（推荐新手）

```bash
git clone https://github.com/Zijie933/DeepCareer.git
cd DeepCareer
cp .env.example .env
# 编辑 .env，填入 OpenAI API Key（可选）和 BOSS_COOKIE
docker-compose up -d
```

启动后访问：
- Web 界面：http://localhost:3000
- API 文档（Swagger）：http://localhost:8001/docs

### 本地开发

```bash
# Python 虚拟环境
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
playwright install chromium
pip install -e .

# 配置环境变量
cp .env.example .env

# 初始化数据库
psql -U admin -d deepcareer -f database/init_db.sql

# 启动后端
deepcareer serve -p 8001

# 另开终端，启动前端
cd frontend
npm install
npm run dev
```

## 快速开始

最快捷的体验方式：

```bash
# 1. 克隆并用 Docker 启动
git clone https://github.com/Zijie933/DeepCareer.git
cd DeepCareer
cp .env.example .env
docker-compose up -d

# 2. 验证 API 是否正常运行
curl http://localhost:8001/health

# 3. 上传简历
curl -X POST http://localhost:8001/api/v2/resumes/upload \
  -F "file=@resume.pdf"

# 4. 爬取职位
deepcareer crawl -c "深圳" -k "Python" -n 10

# 5. 执行智能匹配
curl -X POST http://localhost:8001/api/v2/smart-match \
  -H "Content-Type: application/json" \
  -d '{"resume_id": 1, "max_jobs": 5}'
```

## 配置说明

核心环境变量（`.env`）：

| 变量 | 必填 | 说明 |
|------|------|------|
| `OPENAI_API_KEY` | 否 | OpenAI 兼容的 API 密钥，用于 LLM 提取 |
| `MAGIC_ARK_API_KEY` | 否 | 模力方舟 / Gitee AI 密钥，用于向量嵌入和重排 |
| `BOSS_COOKIE` | 爬虫需要 | BOSS 直聘登录后的 Cookie |
| `POSTGRES_HOST` | 是 | PostgreSQL 地址 |
| `POSTGRES_DB` | 是 | 数据库名（默认：deepcareer） |
| `POSTGRES_USER` | 是 | 数据库用户 |
| `POSTGRES_PASSWORD` | 是 | 数据库密码 |

匹配权重（可配置）：

| 维度 | 默认权重 |
|------|----------|
| 职位方向 | 0.30 |
| 技能匹配 | 0.25 |
| 经验匹配 | 0.20 |
| 学历匹配 | 0.15 |
| 语义相似度 | 0.10 |

## 文档导航

| 主题 | 内容 | 链接 |
|------|------|------|
| 技术架构 | 多 Agent 协作、匹配算法、爬虫设计 | [TECHNICAL.md](./TECHNICAL.md) |
| API 参考 | 简历、职位、智能匹配、爬虫端点 | [docs/api](./docs/api) 或 Swagger UI |
| CLI 命令 | crawl, serve, dev, frontend, cities | [TECHNICAL.md#cli](./TECHNICAL.md#cli-command-line-tools) |
| 数据库设计 | 表定义、索引、向量搜索配置 | [database/schema_v2.sql](./database/schema_v2.sql) |

## 贡献

欢迎提交 Issue 和 Pull Request！

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 提交 Pull Request

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=Zijie933%2FDeepCareer&type=Date)](https://star-history.com/#Zijie933/DeepCareer&Date)

## 许可证

本项目采用 MIT 许可证。详见 [LICENSE](./LICENSE) 文件。