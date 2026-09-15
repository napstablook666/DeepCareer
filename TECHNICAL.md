zi# DeepCareer 技术架构文档

> 本文档详细介绍 DeepCareer 的技术架构、核心算法和实现细节。

---

## 目录

- [CLI 命令行工具](#cli-命令行工具)
- [多 Agent 协作架构](#多-agent-协作架构)
- [系统架构](#系统架构)
- [核心模块](#核心模块)
- [匹配算法](#匹配算法)
- [爬虫系统](#爬虫系统)
- [数据模型](#数据模型)
- [API 设计](#api-设计)
- [性能优化](#性能优化)

---

## CLI 命令行工具

DeepCareer 提供强大的命令行工具，支持爬虫、服务启动等多种操作。

### 安装

```bash
# 方式1: pip 安装（推荐）
pip install -e .

# 安装后可直接使用
deepcareer --help

# 方式2: 直接运行
python -m backend.cli --help
```

### 命令一览

| 命令 | 说明 | 示例 |
|------|------|------|
| `crawl` | 爬取 BOSS 直聘职位 | `deepcareer crawl -c 深圳 -k Python` |
| `serve` | 启动后端 API 服务 | `deepcareer serve -p 8001` |
| `dev` | 同时启动前后端（开发模式） | `deepcareer dev` |
| `frontend` | 启动前端开发服务 | `deepcareer frontend` |
| `cities` | 列出支持的城市 | `deepcareer cities` |
| `version` | 显示版本信息 | `deepcareer version` |

---

### crawl - 职位爬取

从 BOSS 直聘爬取职位数据并保存为 JSON。

```bash
deepcareer crawl --city <城市> --keyword <关键词> [选项]
```

#### 参数说明

| 参数 | 缩写 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `--city` | `-c` | ✅ | - | 城市名称（如：北京、上海、深圳） |
| `--keyword` | `-k` | ✅ | - | 搜索关键词（如：Python、Java） |
| `--count` | `-n` | ❌ | 10 | 爬取数量 |
| `--output` | `-o` | ❌ | 自动生成 | 输出文件名 |
| `--concurrent` | - | ❌ | 5 | 详情页并发数 |
| `--cookie` | - | ❌ | 环境变量 | BOSS 直聘 Cookie |
| `--no-detail` | - | ❌ | - | 不获取详情页 |
| `--visible` | - | ❌ | - | 显示浏览器窗口（调试用） |

#### 使用示例

```bash
# 基础用法：爬取深圳 Python 职位
deepcareer crawl -c 深圳 -k Python

# 指定数量和输出文件
deepcareer crawl -c 上海 -k Java -n 20 -o shanghai_java.json

# 快速模式（不获取详情）
deepcareer crawl -c 北京 -k 前端 --no-detail

# 调试模式（显示浏览器）
deepcareer crawl -c 广州 -k 测试 --visible

# 指定 Cookie
deepcareer crawl -c 深圳 -k Python --cookie "your_cookie_here"
```

#### Cookie 配置

Cookie 的优先级：命令行参数 > 环境变量 > .env 文件

```bash
# 方式1: 环境变量
export BOSS_COOKIE='your_cookie_string'

# 方式2: .env 文件
echo 'BOSS_COOKIE=your_cookie_string' >> .env

# 方式3: 命令行参数
deepcareer crawl -c 深圳 -k Python --cookie 'your_cookie'
```

---

### serve - 启动 API 服务

启动 FastAPI 后端服务。

```bash
deepcareer serve [选项]
```

#### 参数说明

| 参数 | 缩写 | 默认值 | 说明 |
|------|------|--------|------|
| `--host` | `-H` | 0.0.0.0 | 监听地址 |
| `--port` | `-p` | 8001 | 监听端口 |
| `--reload` | `-r` | - | 开发模式（代码修改自动重载） |

#### 使用示例

```bash
# 默认启动（端口 8001）
deepcareer serve

# 指定端口
deepcareer serve -p 8080

# 开发模式（自动重载）
deepcareer serve -r

# 完整参数
deepcareer serve -H 127.0.0.1 -p 8001 -r
```

启动后访问：
- API 服务：http://localhost:8001
- Swagger 文档：http://localhost:8001/docs
- ReDoc 文档：http://localhost:8001/redoc

---

### dev - 开发模式

同时启动前端和后端服务，适合本地开发。

```bash
deepcareer dev [选项]
```

#### 参数说明

| 参数 | 缩写 | 默认值 | 说明 |
|------|------|--------|------|
| `--frontend-port` | `-f` | 3000 | 前端端口 |
| `--backend-port` | `-b` | 8001 | 后端端口 |
| `--reload` | `-r` | - | 后端自动重载 |
| `--quiet` | `-q` | - | 静默模式（隐藏子进程输出） |

#### 使用示例

```bash
# 默认启动
deepcareer dev

# 自定义端口
deepcareer dev -f 5173 -b 8080

# 开发模式 + 静默
deepcareer dev -r -q
```

启动后输出：
```
✅ DeepCareer 开发环境已启动!
   前端: http://localhost:3000
   后端: http://localhost:8001
   文档: http://localhost:8001/docs
按 Ctrl+C 停止所有服务
```

---

### frontend - 前端服务

单独启动前端开发服务。

```bash
deepcareer frontend [选项]
```

#### 参数说明

| 参数 | 缩写 | 说明 |
|------|------|------|
| `--install` | `-i` | 先安装 npm 依赖 |

#### 使用示例

```bash
# 直接启动
deepcareer frontend

# 先安装依赖再启动
deepcareer frontend -i
```

---

### cities - 城市列表

列出爬虫支持的所有城市及其代码。

```bash
deepcareer cities
```

输出示例：
```
📍 支持的城市列表：
----------------------------------------
  全国: 100010000
  北京: 101010100
  上海: 101020100
  深圳: 101280600
  广州: 101280100
  杭州: 101210100
  成都: 101270100
  ...
```

---

### version - 版本信息

```bash
deepcareer version
```

输出：
```
DeepCareer v1.0.0
智能职位匹配系统
```

---

### 完整示例流程

```bash
# 1. 安装项目
pip install -e .

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env，填入 BOSS_COOKIE 等配置

# 3. 启动开发环境
deepcareer dev -r

# 4. 或者分别启动
deepcareer serve -p 8001 -r  # 终端1
deepcareer frontend          # 终端2

# 5. 爬取职位数据
deepcareer crawl -c 深圳 -k Python -n 50

# 6. 查看支持的城市
deepcareer cities
```

---

## 多 Agent 协作架构

DeepCareer 采用多智能体（Multi-Agent）协作模式，4 个专业 Agent 各司其职，协同完成智能求职匹配任务。

### 架构概览

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          用户请求（上传简历 + 匹配职位）                    │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         🧠 Agent 协调器（Orchestrator）                   │
│                                                                          │
│   ┌──────────────┐    ┌──────────────┐    ┌──────────────┐              │
│   │   Step 1     │    │   Step 2     │    │   Step 3     │              │
│   │ 简历分析      │───▶│ 搜索策略      │───▶│ 职位匹配      │              │
│   └──────────────┘    └──────────────┘    └──────────────┘              │
│          │                   │                   │                       │
│          ▼                   ▼                   ▼                       │
│   ┌──────────────┐    ┌──────────────┐    ┌──────────────┐              │
│   │ ResumeAnalyzer│   │SearchStrategy│    │  JobMatcher  │              │
│   │   Agent      │    │   Agent      │    │    Agent     │              │
│   └──────────────┘    └──────────────┘    └──────────────┘              │
│                                                   │                      │
│                                                   ▼                      │
│                                          ┌──────────────┐               │
│                                          │   Step 4     │               │
│                                          │ 推理解释      │               │
│                                          └──────────────┘               │
│                                                   │                      │
│                                                   ▼                      │
│                                          ┌──────────────┐               │
│                                          │ReasoningAgent│               │
│                                          └──────────────┘               │
└─────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                          返回匹配结果 + 推荐理由                           │
└─────────────────────────────────────────────────────────────────────────┘
```

### 四大智能体

| Agent | 职责 | 输入 | 输出 |
|-------|------|------|------|
| **ResumeAnalyzer** | 深度分析简历 | 简历文本 | 候选人画像 |
| **SearchStrategy** | 规划搜索策略 | 候选人画像 + 偏好 | 搜索路径 + 权重 |
| **JobMatcher** | 7 维度职位匹配 | 职位 + 画像 + 权重 | 匹配分数 + 详情 |
| **ReasoningAgent** | 生成推荐理由 | 匹配结果 | 推荐文案 + 建议 |

---

### 1. ResumeAnalyzer - 简历分析智能体

深度分析简历，提取结构化的候选人画像。

#### 核心能力

```python
from backend.agents import resume_analyzer

# 1. 完整简历分析
profile = await resume_analyzer.analyze(resume_text)
# 返回: 基本信息、技能图谱、经验分析、职业路径、优劣势...

# 2. 关键词提取（用于职位搜索）
keywords = await resume_analyzer.extract_keywords(resume_text)
# 返回: ["Python", "FastAPI", "后端开发", "微服务", ...]

# 3. 简历质量评估
quality = await resume_analyzer.assess_quality(resume_text)
# 返回: {score: 85, dimensions: {...}, suggestions: [...]}
```

#### 输出结构

```python
{
    "basic_info": {
        "name": "张三",
        "contact": "13912345678",
        "job_intention": "后端开发工程师"
    },
    "skills": {
        "core_skills": [
            {"name": "Python", "proficiency": "精通"},
            {"name": "FastAPI", "proficiency": "高级"}
        ],
        "soft_skills": ["团队协作", "沟通能力"],
        "tech_stack": {
            "languages": ["Python", "Go", "SQL"],
            "frameworks": ["FastAPI", "Django"],
            "tools": ["Docker", "Redis", "PostgreSQL"]
        }
    },
    "experience": {
        "years": 5,
        "industries": ["互联网", "金融科技"],
        "level": "高级",
        "highlights": ["主导微服务架构重构", "性能优化提升300%"]
    },
    "career_path": {
        "current_stage": "高级工程师",
        "development_direction": "技术专家/架构师",
        "potential_transitions": ["技术管理", "解决方案架构师"]
    },
    "strengths": ["技术深度强", "项目经验丰富"],
    "weaknesses": ["管理经验较少"],
    "salary_expectation": {"min": 25000, "max": 35000},
    "recommended_positions": ["后端开发", "架构师", "技术专家"]
}
```

---

### 2. SearchStrategy - 搜索策略智能体

根据候选人画像和偏好，制定多路径搜索策略。

#### 核心能力

```python
from backend.agents import search_strategy

# 规划搜索策略
strategy = await search_strategy.plan_search(
    candidate_profile=profile,  # ResumeAnalyzer 的输出
    preferences={
        "locations": ["深圳", "广州"],
        "salary_min": 25000,
        "company_types": ["大厂", "独角兽"],
        "remote_ok": True
    }
)
```

#### 输出结构

```python
{
    "search_paths": [
        {
            "path_name": "主路径",
            "description": "Python 后端高级职位",
            "priority": 1,
            "keywords": ["Python", "后端", "高级"],
            "job_titles": ["高级后端工程师", "Python开发专家"],
            "experience_range": {"min": 3, "max": 7},
            "salary_range": {"min": 25000, "max": 40000},
            "locations": ["深圳", "广州"],
            "company_types": ["大厂", "独角兽"]
        },
        {
            "path_name": "备选路径",
            "description": "全栈/架构方向",
            "priority": 2,
            "keywords": ["全栈", "架构师"],
            "job_titles": ["全栈工程师", "技术架构师"],
            # ...
        },
        {
            "path_name": "探索路径",
            "description": "技术管理方向",
            "priority": 3,
            "keywords": ["技术经理", "Tech Lead"],
            # ...
        }
    ],
    "dimension_weights": {
        "skills": 0.25,      # 技能匹配权重
        "experience": 0.20,  # 经验匹配权重
        "salary": 0.15,      # 薪资匹配权重
        "location": 0.10,    # 地点匹配权重
        "culture": 0.10,     # 文化匹配权重
        "growth": 0.10,      # 成长潜力权重
        "stability": 0.10    # 稳定性权重
    },
    "search_radius": "适中",
    "rationale": "候选人技术实力强，建议主攻高级后端职位..."
}
```

---

### 3. JobMatcher - 职位匹配智能体

7 维度智能评估候选人与职位的匹配度。

#### 7 大匹配维度

| 维度 | 说明 | 评估要点 |
|------|------|----------|
| **Skills** | 技能匹配 | 必需技能覆盖率、加分技能 |
| **Experience** | 经验匹配 | 年限、行业、项目经验 |
| **Salary** | 薪资匹配 | 期望 vs 提供的薪资范围 |
| **Location** | 地点匹配 | 工作地点便利性 |
| **Culture** | 文化匹配 | 候选人特质 vs 公司文化 |
| **Growth** | 成长潜力 | 职位对职业发展的价值 |
| **Stability** | 稳定性 | 候选人能否稳定胜任 |

#### 核心能力

```python
from backend.agents import job_matcher

# 单个职位匹配
result = await job_matcher.match(
    job=job_object,
    candidate_profile=profile,
    weights=strategy["dimension_weights"]
)

# 批量匹配（并发执行）
results = await job_matcher.batch_match(
    jobs=job_list,
    candidate_profile=profile,
    weights=weights
)
```

#### 输出结构

```python
{
    "overall_score": 82.5,  # 综合得分
    "dimensions": {
        "skills": {
            "score": 90,
            "reason": "核心技能 Python/FastAPI 完全匹配",
            "matched_skills": ["Python", "FastAPI", "PostgreSQL"],
            "missing_skills": ["Kubernetes"]
        },
        "experience": {
            "score": 85,
            "reason": "5年经验满足3-5年要求，有相关项目经验"
        },
        "salary": {
            "score": 75,
            "reason": "期望25-35K，职位提供20-30K，略有差距"
        },
        "location": {
            "score": 100,
            "reason": "深圳南山区，在候选人期望范围内"
        },
        "culture": {
            "score": 80,
            "reason": "技术驱动型公司，与候选人背景契合"
        },
        "growth": {
            "score": 85,
            "reason": "有架构师晋升通道，符合职业规划"
        },
        "stability": {
            "score": 70,
            "reason": "候选人经验略超职位要求，可能有跳槽风险",
            "risks": ["可能觉得挑战不足"]
        }
    },
    "summary": "该职位与候选人高度匹配，技能和经验契合度高...",
    "recommendation": "推荐申请"  # 推荐申请/观望/不推荐
}
```

---

### 4. ReasoningAgent - 推理智能体

生成人性化的推荐理由、改进建议和求职信。

#### 核心能力

```python
from backend.agents import reasoning_agent

# 1. 生成推荐理由（200-300字）
explanation = await reasoning_agent.explain_match(
    job_info=job_dict,
    candidate_profile=profile,
    match_result=match_result
)

# 2. 生成改进建议
improvements = await reasoning_agent.suggest_improvements(
    candidate_profile=profile,
    match_results=all_match_results
)

# 3. 生成求职信（500-800字）
cover_letter = await reasoning_agent.generate_cover_letter(
    job_info=job_dict,
    candidate_profile=profile
)
```

#### 输出示例

**推荐理由：**
```
这个职位非常适合您！作为一名拥有5年Python后端开发经验的工程师，您的技术栈
与该职位高度匹配。特别是您在微服务架构和性能优化方面的经验，正是该公司目前
急需的能力。

您的优势在于：扎实的Python基础、丰富的FastAPI实战经验、以及在金融科技领域
的业务理解。这些都将帮助您快速上手。

需要注意的是：该职位要求Kubernetes经验，建议您在面试前补充相关知识。此外，
薪资范围略低于您的期望，可以在面试中争取更好的待遇。

职业发展建议：该公司有清晰的技术晋升通道，2-3年内有望晋升为架构师，与您的
职业规划高度契合。
```

**改进建议：**
```python
{
    "skill_gaps": [
        "学习 Kubernetes 容器编排",
        "深入了解云原生架构",
        "补充系统设计面试技巧"
    ],
    "experience_suggestions": [
        "参与开源项目提升影响力",
        "争取主导一个完整项目"
    ],
    "resume_improvements": [
        "量化项目成果（如：性能提升300%）",
        "突出技术深度而非广度",
        "添加技术博客/GitHub链接"
    ],
    "career_advice": [
        "3年内冲击架构师职位",
        "考虑获取云平台认证（AWS/阿里云）"
    ]
}
```

---

### Agent 协作流程

完整的智能匹配流程：

```python
async def smart_match_workflow(resume_text: str, preferences: dict):
    """智能匹配完整流程"""
    
    # Step 1: 简历分析
    profile = await resume_analyzer.analyze(resume_text)
    keywords = await resume_analyzer.extract_keywords(resume_text)
    
    # Step 2: 规划搜索策略
    strategy = await search_strategy.plan_search(profile, preferences)
    
    # Step 3: 搜索职位（爬虫 + 数据库）
    jobs = await search_jobs(
        keywords=keywords,
        paths=strategy["search_paths"]
    )
    
    # Step 4: 批量匹配
    match_results = await job_matcher.batch_match(
        jobs=jobs,
        candidate_profile=profile,
        weights=strategy["dimension_weights"]
    )
    
    # Step 5: 排序并筛选 Top N
    top_matches = sorted(
        match_results,
        key=lambda x: x["overall_score"],
        reverse=True
    )[:10]
    
    # Step 6: 生成推荐理由
    for match in top_matches:
        match["explanation"] = await reasoning_agent.explain_match(
            job_info=match["job"],
            candidate_profile=profile,
            match_result=match
        )
    
    # Step 7: 生成改进建议
    improvements = await reasoning_agent.suggest_improvements(
        candidate_profile=profile,
        match_results=top_matches
    )
    
    return {
        "profile": profile,
        "strategy": strategy,
        "matches": top_matches,
        "improvements": improvements
    }
```

### Agent 设计原则

| 原则 | 说明 |
|------|------|
| **单一职责** | 每个 Agent 只负责一个领域 |
| **松耦合** | Agent 之间通过标准数据结构通信 |
| **可替换** | 可以用规则引擎替代 LLM Agent |
| **可降级** | LLM 调用失败时有默认策略兜底 |
| **可观测** | 每个 Agent 有详细的日志输出 |

---

## 系统架构

### 整体架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                         客户端层                                  │
│                   React + Ant Design                             │
└────────────────────────┬────────────────────────────────────────┘
                         │ HTTP / SSE
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                      API 网关层 (FastAPI)                         │
├─────────────────────────────────────────────────────────────────┤
│  简历API  │  职位API  │  匹配API  │  爬虫API  │  健康检查         │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                        服务层                                     │
├──────────────┬──────────────┬──────────────┬──────────────────┤
│ ExtractorSvc │  MatcherSvc  │ EmbeddingSvc │   CrawlerSvc     │
│  信息提取     │   匹配算法    │   向量服务    │    爬虫服务       │
└──────┬───────┴──────┬───────┴──────┬───────┴──────┬───────────┘
       │              │              │              │
       └──────────────┴──────────────┴──────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                      数据存储层                                   │
├──────────────┬──────────────┬──────────────┬──────────────────┤
│ PostgreSQL   │   pgvector   │    Redis     │   文件存储        │
│ (关系数据)    │  (向量索引)   │   (缓存)     │  (简历文件)       │
└──────────────┴──────────────┴──────────────┴──────────────────┘
```

### 技术选型

| 层级 | 技术 | 选型理由 |
|------|------|----------|
| Web 框架 | FastAPI | 原生异步、自动文档、类型安全 |
| ORM | SQLAlchemy 2.0 | 异步支持、成熟稳定 |
| 数据库 | PostgreSQL + pgvector | 向量搜索原生支持 |
| 爬虫 | Playwright | 渲染 JS、反检测能力强 |
| Embedding / Rerank | 模力方舟 Serverless API | `bge-m3` + `bge-reranker-v2-m3` |
| 缓存 | Redis | 高性能、支持过期 |

---

## 核心模块

### 1. 信息提取服务 (ExtractorService)

负责从简历和职位描述中提取结构化信息。

#### 双模式提取

```python
# 模式1: 规则提取（默认）
# - 免费、快速（毫秒级）
# - 准确率 80-85%

# 模式2: LLM 提取（可选）
# - 高精度（95%+）
# - 有成本（~$0.001/次）
```

#### 简历提取字段

```python
{
    "name": "张三",
    "phone": "13912345678",
    "email": "zhangsan@example.com",
    "current_position": "后端开发工程师",
    "years_experience": 5,
    "education": "本科",
    "skills": ["Python", "FastAPI", "PostgreSQL"],
    "job_intention": {
        "positions": ["后端开发", "全栈开发"],
        "cities": ["深圳", "广州"],
        "salary_range": "25-35K"
    }
}
```

#### 职位提取字段

```python
{
    "title": "Python后端工程师",
    "required_skills": ["Python", "Django", "MySQL"],
    "preferred_skills": ["Redis", "Docker"],
    "experience_required": "3-5年",
    "education_required": "本科",
    "salary_range": {"min": 20000, "max": 35000}
}
```

---

### 2. 匹配服务 (MatcherService)

核心匹配算法，5 维度评分。

#### 权重配置

```python
weights = {
    'position': 0.30,   # 职位方向 30% - 最重要
    'skills': 0.25,     # 技能匹配 25%
    'experience': 0.20, # 经验匹配 20%
    'education': 0.15,  # 学历匹配 15%
    'semantic': 0.10    # 语义相似度 10%
}
```

#### 匹配流程

```
简历数据 + 职位数据
        ↓
┌───────────────────────────────────────┐
│ 1. 职位方向匹配 (position_match)       │
│    - 识别简历职位类别                   │
│    - 识别职位类别                       │
│    - 计算匹配度                         │
│    - 技术→非技术 = 10分（严重不匹配）    │
└───────────────────────────────────────┘
        ↓ (如果 < 30分，直接返回低分)
┌───────────────────────────────────────┐
│ 2. 技能匹配 (skills_match)             │
│    - 必需技能匹配率                     │
│    - 加分技能匹配                       │
└───────────────────────────────────────┘
        ↓
┌───────────────────────────────────────┐
│ 3. 经验匹配 (experience_match)         │
│    - 年限比较                          │
│    - 区间判断                          │
└───────────────────────────────────────┘
        ↓
┌───────────────────────────────────────┐
│ 4. 学历匹配 (education_match)          │
│    - 学历等级比较                       │
│    - 达标/超出/不足                     │
└───────────────────────────────────────┘
        ↓
┌───────────────────────────────────────┐
│ 5. 语义相似度 (semantic_match)         │
│    - Embedding 余弦相似度              │
│    - 补充文本层面的匹配                 │
└───────────────────────────────────────┘
        ↓
    加权求和 → 总分
```

---

### 3. 向量服务 (EmbeddingService)

通过模力方舟远程接口生成 Embedding，并对候选职位执行 Rerank。

#### 模型选择

```python
# 模力方舟免费模型
embedding_model = "bge-m3"
rerank_model = "bge-reranker-v2-m3"
# bge-m3 向量维度: 1024
```

#### 使用方式

```python
from backend.utils.embedding_service import get_embedding_service

service = get_embedding_service()

# 单个文本
embedding = service.create_embedding("Python后端开发工程师")
# → [0.123, -0.456, ...] (1024维)

# 批量文本
embeddings = service.create_embedding([
    "Python后端开发",
    "Java开发工程师"
])

# 对候选职位重排
ranked = service.rerank(
    query="Python后端开发工程师",
    documents=["Python API 开发", "Java 前端开发"],
    top_n=2,
)
```

#### 相似度计算

```python
# 余弦相似度
similarity = service.cosine_similarity(embedding1, embedding2)
# → 0.85 (范围 0-1)
```

---

### 4. 爬虫服务 (BossWebCrawlerPlaywright)

基于 Playwright 的 BOSS 直聘爬虫。

#### 反爬虫策略

| 策略 | 实现 | 效果 |
|------|------|------|
| 随机 UA | 8 种主流浏览器 UA 轮换 | 避免指纹识别 |
| 智能延迟 | 每次请求 1-3 秒随机延迟 | 模拟人工操作 |
| Cookie 认证 | 支持登录态 Cookie | 获取完整数据 |
| 反检测脚本 | 隐藏 webdriver 特征 | 绕过检测 |
| 请求重试 | 失败自动重试 3 次 | 提高成功率 |

#### 使用示例

```python
async with BossWebCrawlerPlaywright(
    min_delay=1.0,
    max_delay=2.0,
    headless=True,
    cookie_string=BOSS_COOKIE,
    target_city="深圳"
) as crawler:
    # 搜索职位
    jobs = await crawler.search_jobs(
        keyword="Python",
        city="深圳",
        page=1,
        auto_scroll=True,
        max_scroll=5
    )
    
    # 获取详情
    detail = await crawler.get_job_detail(job_url)
```

#### 支持城市

```python
CITY_CODES = {
    # 全国
    "全国": "100010000",
    
    # 一线城市
    "北京": "101010100",
    "上海": "101020100",
    "广州": "101280100",
    "深圳": "101280600",
    
    # 新一线城市
    "杭州": "101210100",
    "成都": "101270100",
    "重庆": "101040100",
    "武汉": "101200100",
    "西安": "101110100",
    "苏州": "101190400",
    "南京": "101190100",
    "天津": "101030100",
    "郑州": "101180100",
    "长沙": "101250100",
    "东莞": "101281600",
    "佛山": "101280800",
    "宁波": "101210400",
    "青岛": "101120200",
    "沈阳": "101070100",
    
    # 二线城市
    "合肥": "101220100",
    "厦门": "101230200",
    "无锡": "101190200",
    "昆明": "101290100",
    "大连": "101070200",
    "福州": "101230100",
    "哈尔滨": "101050100",
    "济南": "101120100",
    "温州": "101210700",
    "石家庄": "101090100",
    "南宁": "101300100",
    "长春": "101060100",
    "泉州": "101230500",
    "贵阳": "101260100",
    "南昌": "101240100",
    "金华": "101210900",
    "常州": "101191100",
    "珠海": "101280700",
    "惠州": "101280300",
    "嘉兴": "101210300",
    "南通": "101190500",
    "中山": "101281700",
    "太原": "101100100",
    "兰州": "101160100",
    "徐州": "101190800",
    "台州": "101210600",
    "绍兴": "101210500",
    "烟台": "101120500",
    "海口": "101310100",
    
    # 其他城市
    "乌鲁木齐": "101130100",
    "呼和浩特": "101080100",
    "银川": "101170100",
    "西宁": "101150100",
    "拉萨": "101140100",
    "三亚": "101310200",
}
```

> 共支持 **60+** 个城市，覆盖全国主要一二线城市。

---

## 匹配算法

### 职位方向匹配

最重要的匹配维度，防止跨领域错配。

#### 职位类别定义

```python
position_categories = {
    # 技术类
    '后端开发': ['后端', 'java', 'python', 'go', 'php', ...],
    '前端开发': ['前端', 'react', 'vue', 'javascript', ...],
    '测试开发': ['测试', 'qa', '自动化测试', ...],
    '算法/AI': ['算法', 'ai', '机器学习', 'nlp', ...],
    # ...
    
    # 非技术类
    '产品经理': ['产品', 'pm', 'product manager', ...],
    '设计师': ['设计', 'ui', 'ux', '视觉', ...],
    '运营': ['运营', '用户运营', '内容运营', ...],
    # ...
}
```

#### 匹配规则

| 场景 | 得分 | 说明 |
|------|------|------|
| 完全匹配 | 100 | 后端→后端 |
| 同为技术类 | 60 | 后端→前端 |
| 同为非技术类 | 40 | 产品→运营 |
| 技术↔非技术 | 10 | 后端→产品（严重不匹配）|

```python
# 关键逻辑
if position_score < 30:
    # 方向不匹配，直接返回低分
    total_score = position_score * 0.5  # 最高15分
    return total_score
```

### 技能匹配

```python
def _match_skills(resume_skills, required_skills, preferred_skills):
    # 必需技能匹配
    required_matched = set(resume_skills) & set(required_skills)
    required_score = len(required_matched) / len(required_skills) * 100
    
    # 加分技能
    preferred_matched = set(resume_skills) & set(preferred_skills)
    bonus = len(preferred_matched) * 5  # 每个加分技能 +5
    
    return min(100, required_score + bonus)
```

### 经验匹配

```python
def _match_experience(resume_years, job_requirement):
    # 解析要求: "3-5年" → (3, 5)
    min_years, max_years = parse_experience(job_requirement)
    
    if resume_years >= min_years and resume_years <= max_years + 2:
        return 100  # 完美匹配
    elif resume_years >= min_years - 1:
        return 80   # 略低于要求
    elif resume_years >= min_years - 2:
        return 60   # 差距较大
    else:
        return 40   # 经验不足
```

### 学历匹配

```python
EDUCATION_LEVELS = {
    "博士": 5,
    "硕士": 4,
    "本科": 3,
    "大专": 2,
    "高中": 1
}

def _match_education(resume_edu, job_edu):
    resume_level = EDUCATION_LEVELS.get(resume_edu, 0)
    job_level = EDUCATION_LEVELS.get(job_edu, 0)
    
    if resume_level >= job_level:
        return 100  # 达标或超出
    elif resume_level == job_level - 1:
        return 70   # 差一级
    else:
        return 40   # 差距较大
```

---

## 数据模型

### 简历表 (resumes_v2)

```sql
CREATE TABLE resumes_v2 (
    id SERIAL PRIMARY KEY,
    
    -- 文件信息
    file_name VARCHAR(255),
    file_type VARCHAR(20),
    file_path VARCHAR(500),
    full_text TEXT,
    
    -- 结构化数据
    structured_data JSONB,
    
    -- 提取元数据
    extraction_method VARCHAR(20),  -- 'rule' | 'llm'
    extraction_confidence FLOAT,
    
    -- 向量
    text_embedding VECTOR(1024),
    
    -- 时间戳
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP
);

-- 向量索引
CREATE INDEX ON resumes_v2 
USING ivfflat (text_embedding vector_cosine_ops);
```

### 职位表 (jobs_v2)

```sql
CREATE TABLE jobs_v2 (
    id SERIAL PRIMARY KEY,
    
    -- 基本信息
    title VARCHAR(255),
    company_name VARCHAR(255),
    city VARCHAR(50),
    salary_text VARCHAR(100),
    
    -- 要求
    experience_required VARCHAR(50),
    education_required VARCHAR(50),
    
    -- 详情
    job_description TEXT,
    job_url VARCHAR(500),
    
    -- 结构化数据
    structured_data JSONB,
    
    -- 向量
    description_embedding VECTOR(1024),
    
    -- 来源
    platform VARCHAR(50),
    external_id VARCHAR(100),
    
    -- 状态
    is_active BOOLEAN DEFAULT TRUE,
    crawled_at TIMESTAMP DEFAULT NOW()
);

-- 索引
CREATE INDEX ON jobs_v2 (city);
CREATE INDEX ON jobs_v2 (is_active);
CREATE INDEX ON jobs_v2 
USING ivfflat (description_embedding vector_cosine_ops);
```

---

## API 设计

### 流式匹配 API

使用 Server-Sent Events (SSE) 实现实时推送。

#### 请求

```http
POST /api/v2/smart-match/stream
Content-Type: application/json

{
    "resume_id": 1,
    "enable_crawler": true,
    "min_jobs": 10,
    "qualified_threshold": 60,
    "min_display_score": 30
}
```

#### 响应（SSE 流）

```
data: {"type": "start", "message": "开始匹配..."}

data: {"type": "db_matches", "data": {"matches": [...], "qualified_count": 5}}

data: {"type": "crawling", "message": "合格职位不足，正在搜索更多..."}

data: {"type": "crawler_match", "data": {"job_id": 10, "match_score": 75.5, ...}}

data: {"type": "complete", "total_qualified": 12}
```

#### 前端消费

```javascript
const eventSource = new EventSource('/api/v2/smart-match/stream');

eventSource.onmessage = (event) => {
    const data = JSON.parse(event.data);
    
    switch (data.type) {
        case 'db_matches':
            setMatches(data.data.matches);
            break;
        case 'crawler_match':
            addMatch(data.data);
            break;
        case 'complete':
            setLoading(false);
            break;
    }
};
```

---

## 性能优化

### 1. 向量搜索优化

```sql
-- IVFFlat 索引（适合百万级数据）
CREATE INDEX ON jobs_v2 
USING ivfflat (description_embedding vector_cosine_ops)
WITH (lists = 100);

-- 查询时设置探测数
SET ivfflat.probes = 10;
```

### 2. 数据库连接池

```python
# config.py
DB_POOL_SIZE = 10
DB_MAX_OVERFLOW = 20

# 异步连接池
engine = create_async_engine(
    DATABASE_URL,
    pool_size=DB_POOL_SIZE,
    max_overflow=DB_MAX_OVERFLOW
)
```

### 3. 批量操作

```python
# 批量插入职位
async def batch_create_jobs(jobs: List[dict]):
    async with async_session() as db:
        db.add_all([JobV2(**job) for job in jobs])
        await db.commit()
```

### 4. 缓存策略

```python
# Redis 缓存匹配结果
cache_key = f"match:{resume_id}:{job_id}"
cached = await redis.get(cache_key)

if cached:
    return json.loads(cached)

result = await compute_match(resume, job)
await redis.setex(cache_key, 3600, json.dumps(result))
```

---

## 部署架构

### 生产环境推荐

```
                    ┌─────────────┐
                    │   Nginx     │
                    │  (反向代理)  │
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
        ┌─────▼─────┐ ┌────▼────┐ ┌────▼────┐
        │  App 1    │ │  App 2  │ │  App 3  │
        │ (FastAPI) │ │(FastAPI)│ │(FastAPI)│
        └─────┬─────┘ └────┬────┘ └────┬────┘
              │            │            │
              └────────────┼────────────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
        ┌─────▼─────┐ ┌────▼────┐ ┌────▼────┐
        │PostgreSQL │ │  Redis  │ │   S3    │
        │ (主从)    │ │ (集群)  │ │ (文件)  │
        └───────────┘ └─────────┘ └─────────┘
```

### 资源估算

| 组件 | 最小配置 | 推荐配置 |
|------|----------|----------|
| API 服务 | 2C4G × 2 | 4C8G × 3 |
| PostgreSQL | 2C4G | 4C16G |
| Redis | 1C2G | 2C4G |
| 总计 | 7C14G | 18C44G |

---

## 监控指标

### 关键指标

| 指标 | 阈值 | 说明 |
|------|------|------|
| API 响应时间 | < 500ms | P95 |
| 匹配计算时间 | < 100ms | 单次 |
| 爬虫成功率 | > 90% | |
| 数据库连接数 | < 80% | 池使用率 |

### 日志格式

```python
# 结构化日志
logger.info(
    "匹配完成",
    extra={
        "resume_id": 1,
        "job_count": 50,
        "qualified_count": 12,
        "duration_ms": 150
    }
)
```

---

## 扩展计划

### 短期

- [ ] 支持更多招聘平台（拉勾、智联）
- [ ] 简历评分功能
- [ ] 职位收藏功能

### 中期

- [ ] 用户反馈学习
- [ ] 推荐理由生成（LLM）
- [ ] 简历优化建议

### 长期

- [ ] 图神经网络职位关系
- [ ] 强化学习搜索策略
- [ ] 多语言支持

---

**文档版本**: v1.0.0  
**最后更新**: 2025-12-25
