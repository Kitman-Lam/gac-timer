# Claude.md — 全局开发规范

## 一、个人开发习惯

### 技术栈
- 后端：Python + FastAPI，使用 uv 进行包管理与虚拟环境管理
- 前端：TypeScript + Next.js

### 代码风格
遵循各语言和框架最流行的社区规范：
- Python：遵循 PEP 8，使用 Black 格式化，变量与函数命名采用 snake_case
- TypeScript：遵循 Airbnb 风格指南，使用 Prettier 格式化，变量与函数命名采用 camelCase，组件命名采用 PascalCase
- 注释语言：英文

---

## 二、跨项目目录结构

所有项目遵循以下统一目录结构：

```
project/
├── backend/                # FastAPI 后端
│   ├── app/
│   │   ├── api/            # 路由层
│   │   ├── core/           # 配置、依赖注入
│   │   ├── models/         # 数据库模型
│   │   ├── schemas/        # Pydantic 数据结构
│   │   ├── services/       # 业务逻辑层
│   │   └── main.py
│   ├── tests/
│   ├── pyproject.toml      # uv 项目配置
│   └── uv.lock             # 依赖锁文件（提交 Git）
├── frontend/               # Next.js 前端
│   ├── app/                # App Router 页面
│   ├── components/         # 可复用组件
│   ├── lib/                # 工具函数
│   ├── types/              # TypeScript 类型定义
│   └── public/
├── .trae/
│   ├── agents/             # 各 Agent 描述文件
│   ├── rules/
│   └── mcp.json
├── docs/
│   └── handoff_report.md   # 人工介入报告输出文件
├── .env                    # 环境变量（不提交 Git）
├── .env.example            # 环境变量模板（提交 Git）
├── .gitignore              # 包含 .env、.venv
├── AGENT.md                # 项目级规范
└── Claude.md               # 全局规范引用说明
```

---

## 三、多智能体架构

### 流程概览

本架构为三智能体系统，流程起点是通过 Agent Skill 手动生成的详细需求文档，作为整个流程的唯一输入来源。

```
需求文档（Agent Skill 生成）
        ↓
   Planner（技术规格转译）
        ↓
   Sprint 合约协商
        ↓
   Generator（逐 Sprint 构建）
        ↓
   Evaluator（验收 + 反馈）
        ↓
   通过 → 下一 Sprint / 全部完成
   失败 → 重试（最多 3 次）→ 人工介入
```

### 角色职责边界

**需求文档**
由开发者通过 Agent Skill 手动生成，涵盖产品功能、业务逻辑与用户故事。所有 Agent 只读，不得修改或重新解释其中内容。

**Planner**
接收需求文档，输出技术规格文档，包括技术栈决策、Sprint 划分和每个 Sprint 的验收标准。只做技术转译，不重新解释需求。如需求文档存在技术冲突，以"待确认项"列出，等待人工确认后继续。

**Generator**
接收技术规格文档，按 Sprint 逐步构建可运行的功能模块。每个 Sprint 开始前须与 Evaluator 完成合约协商，获批后方可开始编码。Sprint 结束时生成移交文件。

**Evaluator**
负责 Sprint 合约审核与功能验收两个职责。使用 Playwright 以真实用户路径测试应用，对每条验收标准给出明确的通过或失败判定。同一 Sprint 最多允许 Generator 重试 3 次，达到上限后触发人工介入。

### 移交文件格式

每个 Sprint 结束时，Generator 生成移交文件，包含以下固定字段：

```json
{
  "sprint": "Sprint 编号与标题",
  "completed": ["已完成功能列表，对应验收标准条目"],
  "code_structure": "当前代码结构简述",
  "known_issues": ["已知遗留问题或技术债"],
  "next_sprint_prerequisites": ["下一 Sprint 启动所需的环境前提"]
}
```

---

## 四、跨项目持久约定

### Git 提交信息格式
遵循 Conventional Commits 规范：

```
<type>(<scope>): <subject>

type: feat | fix | chore | docs | refactor | test | style
scope: 可选，如 auth、api、ui
subject: 简短描述，英文，不超过 72 字符
```

示例：
- `feat(auth): add JWT refresh token support`
- `fix(api): handle null response from payment gateway`
- `chore: update dependencies`

### Python 包管理
- 统一使用 uv 管理依赖与虚拟环境
- 不使用 pip 直接安装，所有依赖通过 `uv add` 添加
- 依赖锁文件 `uv.lock` 提交 Git
- 虚拟环境目录 `.venv` 不提交 Git，加入 `.gitignore`

### 环境变量管理
- 所有环境变量统一通过 `.env` 文件管理
- `.env` 不提交 Git，`.env.example` 提交 Git 作为模板
- 变量命名全大写 + 下划线，按模块前缀分组，如 `DB_HOST`、`AUTH_SECRET_KEY`

### API 响应格式
所有接口遵循统一的 JSON 响应结构：

```json
{
  "success": true,
  "data": {},
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable message"
  },
  "meta": {
    "page": 1,
    "total": 100
  }
}
```

- 成功响应：`success: true`，`data` 包含业务数据，`error` 为 null
- 失败响应：`success: false`，`data` 为 null，`error` 包含错误码与描述
- 分页响应：`meta` 包含分页信息，其他情况 `meta` 可省略

---

## 五、人工介入机制

### 触发条件
以下任意情况发生时，流程立即暂停并触发人工介入：
- 同一 Sprint 内 Generator 重试达到 3 次仍存在失败项
- Evaluator 在同一失败项上检测到两次相同的修复方案（无效重试）
- Planner 输出的"待确认项"未经人工确认
- 技术栈之外出现无法自行解决的新依赖冲突

### 上报方式
触发人工介入时，同时执行以下两个动作：
1. 在对话窗口直接输出介入报告
2. 将报告写入 `docs/handoff_report.md`

### 介入报告格式

```markdown
# 人工介入报告

## 基本信息
- Sprint：[编号与标题]
- 触发原因：[重试上限 / 无效重试 / 待确认项 / 依赖冲突]
- 时间：[生成时间]

## 未解决的失败项
- [失败项描述，含触发路径、实际行为、期望行为]

## 已尝试的修复摘要
- 第 1 次：[修复方式]
- 第 2 次：[修复方式]
- 第 3 次：[修复方式]

## 建议的人工处理方向
- [具体建议]
```

---

## 六、禁止行为

以下行为适用于所有项目的所有 Agent，任何情况下均不得违反：

- 不修改需求文档原文，需求文档只读
- 不在没有 Sprint 合约的情况下开始编码
- 不以功能存根（stub）代替真实实现后静默交付
- 不在同一失败项上接受两次相同的修复方案
- 不降低验收标准以使 Sprint 强制通过
- 不自行替换已约定的技术栈
- 不使用 pip 直接安装依赖，必须通过 uv 管理
- 不修改 `.env` 文件中已有的变量值，如需新增变量须在 `.env.example` 中同步添加
- **不得在未经人工确认的情况下删除数据库数据**

## 七、容器化管理

### 基本约定
- 统一使用 Docker + Docker Compose 进行容器化管理
- 测试环境与生产环境使用独立的 Compose 文件：
  - `docker-compose.yml`：测试环境
  - `docker-compose.prod.yml`：生产环境
- 不将 `.env` 文件或任何密钥打包进镜像
- 所有服务的环境变量通过 `env_file` 注入

### 镜像管理
- 镜像统一推送至 Docker Hub
- 镜像命名规范：`<dockerhub-username>/<project-name>-<service>:<tag>`
  - 示例：`username/myapp-backend:v1.0.0`、`username/myapp-frontend:latest`
- tag 规范：正式版本使用语义化版本号（`v1.0.0`），开发版本使用 `latest`

### 目录结构补充
每个项目根目录新增以下文件：
- `docker-compose.yml`：测试环境编排
- `docker-compose.prod.yml`：生产环境编排
- `backend/Dockerfile`
- `frontend/Dockerfile`

### 构建与部署流程（本地服务器）
在服务器上通过手动脚本执行部署，流程如下：

1. 拉取最新代码：`git pull origin main`
2. 构建镜像：`docker compose -f docker-compose.prod.yml build`
3. 推送镜像至 Docker Hub：`docker compose -f docker-compose.prod.yml push`
4. 重启服务：`docker compose -f docker-compose.prod.yml up -d`
5. 清理旧镜像：`docker image prune -f`

以上步骤封装为 `deploy.sh`，放置于项目根目录并提交 Git。

### 禁止行为补充
- 不在生产环境 Compose 文件中暴露非必要端口
- 不在 Dockerfile 中硬编码环境变量值
- 不直接在服务器上修改代码，所有变更必须通过 Git 流程