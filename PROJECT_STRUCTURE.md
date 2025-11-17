# YFAI 项目结构说明

> **更新时间**: 2025-11-17
> **项目版本**: v0.2.0

---

## 📁 目录结构

```
yfai/
├── yfai/                       # 核心代码目录
│   ├── __init__.py
│   ├── __main__.py            # 程序入口 (python -m yfai)
│   ├── main.py                # 主函数
│   │
│   ├── app/                   # PyQt6 UI 层
│   │   ├── __init__.py
│   │   ├── main_window.py    # 主窗口
│   │   └── widgets/          # UI 组件
│   │       ├── chat_widget.py        # 聊天界面
│   │       ├── agents_page.py        # 智能体管理
│   │       ├── jobs_page.py          # 任务记录
│   │       ├── assistants_page.py    # AI助手
│   │       ├── sessions_page.py      # 会话管理
│   │       ├── models_page.py        # 模型管理
│   │       ├── automation_page.py    # 自动化
│   │       ├── connector_page.py     # 连接器
│   │       ├── knowledge_page.py     # 知识库
│   │       ├── logs_page.py          # 日志
│   │       ├── tools_page.py         # 工具
│   │       ├── settings_page.py      # 设置
│   │       ├── settings_form.py      # 设置表单
│   │       ├── settings_dialog.py    # 设置对话框
│   │       ├── approval_dialog.py    # 审批对话框
│   │       ├── sidebar.py            # 侧边栏
│   │       └── tools_panel.py        # 工具面板
│   │
│   ├── core/                  # 核心模块
│   │   ├── __init__.py
│   │   ├── config.py         # 配置管理
│   │   ├── orchestrator.py   # 对话编排
│   │   └── agent_runner.py   # 智能体运行器
│   │
│   ├── providers/             # LLM Provider 适配器
│   │   ├── __init__.py
│   │   ├── base.py           # 基础抽象
│   │   ├── bailian.py        # 阿里百炼
│   │   ├── ollama.py         # Ollama 本地
│   │   ├── manager.py        # Provider 管理器
│   │   └── defaults.py       # 默认配置
│   │
│   ├── mcp/                   # MCP 客户端
│   │   ├── __init__.py
│   │   ├── client.py         # MCP 客户端
│   │   └── registry.py       # 服务器注册中心
│   │
│   ├── localops/              # 本地控制能力
│   │   ├── __init__.py
│   │   ├── fs.py             # 文件系统
│   │   ├── shell.py          # Shell 脚本
│   │   ├── process.py        # 进程管理
│   │   └── net.py            # 网络工具
│   │
│   ├── security/              # 安全模块
│   │   ├── __init__.py
│   │   ├── guard.py          # 安全守卫
│   │   └── policy.py         # 安全策略
│   │
│   ├── store/                 # 数据存储
│   │   ├── __init__.py
│   │   ├── db.py             # 数据库管理
│   │   └── indexer.py        # 向量索引
│   │
│   ├── connectors/            # 连接器
│   │   ├── __init__.py
│   │   ├── base.py           # 基础抽象
│   │   └── http.py           # HTTP 连接器
│   │
│   ├── automation/            # 自动化调度
│   │   ├── __init__.py
│   │   └── scheduler.py      # 调度器
│   │
│   ├── tests/                 # 测试目录 (待完善)
│   │   └── __init__.py
│   │
│   └── scripts/               # 脚本目录 (待添加)
│       └── __init__.py
│
├── configs/                   # 配置文件
│   ├── config.yaml           # 主配置 (运行时)
│   ├── config.example.yaml   # 配置示例
│   ├── McpRegistry.yaml      # MCP 服务器注册
│   ├── .env                  # 环境变量 (运行时，不提交)
│   └── .env.example          # 环境变量示例
│
├── docs/                      # 文档目录 (优化后)
│   ├── design/               # 设计文档
│   │   ├── 设计文档.md
│   │   └── 技术栈与实现规划.md
│   ├── development/          # 开发文档
│   │   ├── 功能清单.md
│   │   └── 缺失功能清单.md
│   └── user-guide/           # 用户文档
│       └── 操作手册.md
│
├── data/                      # 数据目录
│   ├── yfai.db               # SQLite 数据库 (运行时)
│   └── vectors/              # 向量索引 (运行时)
│
├── logs/                      # 日志目录 (运行时)
│   ├── yfai.log
│   └── yfai.log.1
│
├── old/                       # 已废弃/临时文档 (待删除)
│   ├── prototype/            # HTML 原型 (已实现 PyQt6)
│   ├── CODE_ANALYSIS_REPORT.md
│   ├── CRITICAL_ISSUES_SUMMARY.md
│   ├── ANALYSIS_QUICK_START.md
│   ├── ISSUES_CHECKLIST.csv
│   ├── 改造建设方案.md
│   ├── 改造计划.md
│   └── 优化建议.md
│
├── .gitignore                 # Git 忽略配置
├── pyproject.toml             # Poetry 项目配置
├── requirements.txt           # pip 依赖清单
├── run.py                     # 启动脚本
├── test_integration.py        # 集成测试
│
├── README.md                  # 项目介绍
├── QUICK_START.md             # 快速开始
├── INSTALLATION.md            # 安装指南
├── PROJECT_SUMMARY.md         # 项目总结
├── FEATURES_STATUS.md         # 功能清单 (本文档的补充)
├── PROJECT_STRUCTURE.md       # 项目结构说明 (本文档)
├── DEVELOPMENT_ROADMAP.md     # 开发路线图
├── CHANGELOG.md               # 更新日志
└── AGENTS.md                  # 智能体说明
```

---

## 📊 代码统计

### 按模块统计
| 模块 | 文件数 | 代码行数 | 功能描述 |
|------|--------|----------|----------|
| `yfai/app/` | 21 | ~5,900 | PyQt6 UI 界面 |
| `yfai/core/` | 3 | ~1,300 | 核心调度逻辑 |
| `yfai/providers/` | 6 | ~1,000 | LLM Provider 适配 |
| `yfai/store/` | 2 | ~980 | 数据库和向量索引 |
| `yfai/security/` | 2 | ~390 | 安全守卫和策略 |
| `yfai/localops/` | 4 | ~800 | 本地控制能力 |
| `yfai/mcp/` | 2 | ~320 | MCP 客户端 |
| `yfai/automation/` | 1 | ~180 | 自动化调度 |
| `yfai/connectors/` | 2 | ~120 | 连接器框架 |
| **总计** | **54** | **~11,200** | |

### 文档统计
| 类型 | 数量 | 描述 |
|------|------|------|
| 根目录 Markdown | 10 | 项目说明、指南、总结 |
| docs/ 文档 | 5 | 设计、开发、用户文档 |
| 配置文件 | 5 | YAML、ENV 配置 |
| 测试文件 | 1 | 集成测试 |

---

## 🗂️ 核心模块说明

### 1. `yfai/app/` - UI 层
**职责**: 用户界面、交互逻辑

**关键文件**:
- `main_window.py` (659行): 主窗口，包含菜单、工具栏、状态栏
- `widgets/chat_widget.py` (434行): 聊天界面，流式输出
- `widgets/agents_page.py` (843行): 智能体管理，创建/编辑/运行
- `widgets/jobs_page.py` (287行): 任务运行记录
- `widgets/assistants_page.py` (327行): AI 助手配置
- `widgets/sessions_page.py` (319行): 会话历史管理
- `widgets/knowledge_page.py` (366行): 知识库管理
- `widgets/automation_page.py` (543行): 自动化任务
- `widgets/connector_page.py` (518行): 连接器管理
- `widgets/settings_page.py` (378行): 系统设置

**特点**:
- 使用 PyQt6 框架
- qasync 异步支持
- 信号槽机制

---

### 2. `yfai/core/` - 核心层
**职责**: 对话编排、智能体运行、配置管理

**关键文件**:
- `orchestrator.py` (532行): 核心调度器
  - 会话管理
  - 消息路由
  - 工具执行
  - Provider 选择

- `agent_runner.py` (655行): 智能体运行器
  - 计划生成
  - 步骤执行
  - Job 记录
  - 执行总结

- `config.py` (116行): 配置管理
  - YAML 加载
  - 环境变量
  - 配置访问

**特点**:
- 依赖注入设计
- 异步编程
- 事务管理

---

### 3. `yfai/providers/` - Provider 层
**职责**: LLM 提供商适配

**关键文件**:
- `base.py` (138行): Provider 基类
- `bailian.py` (204行): 阿里百炼适配器
- `ollama.py` (185行): Ollama 适配器
- `manager.py` (255行): Provider 管理器

**特点**:
- 策略模式
- 统一接口
- 自动路由
- 健康检查

---

### 4. `yfai/store/` - 数据层
**职责**: 数据持久化、向量索引

**关键文件**:
- `db.py` (802行): 数据库管理
  - 10 张数据表
  - SQLAlchemy ORM
  - 会话管理

- `indexer.py` (177行): 向量索引
  - FAISS 索引
  - 向量检索

**数据表**:
1. `sessions` - 会话
2. `messages` - 消息
3. `tool_calls` - 工具调用记录
4. `assistants` - AI 助手
5. `agents` - 智能体
6. `job_runs` - 任务运行记录
7. `job_steps` - 任务步骤
8. `automation_tasks` - 自动化任务
9. `connectors` - 连接器
10. `knowledge_bases` - 知识库
11. `knowledge_chunks` - 知识库分块

---

### 5. `yfai/security/` - 安全层
**职责**: 权限控制、审批、审计

**关键文件**:
- `guard.py` (313行): 安全守卫
  - 权限检查
  - 审批请求
  - 风险评估
  - 审计日志

- `policy.py` (78行): 安全策略
  - 危险操作识别
  - 路径白名单
  - 风险等级

**风险等级**:
- LOW: 读操作
- MEDIUM: 写操作
- HIGH: 删除、进程管理
- CRITICAL: 系统级操作

---

### 6. `yfai/localops/` - 本地操作层
**职责**: 本地控制能力

**关键文件**:
- `fs.py` (252行): 文件系统操作
- `shell.py` (182行): Shell 脚本执行
- `process.py` (176行): 进程管理
- `net.py` (191行): 网络工具

**特点**:
- 白名单保护
- 异步执行
- 输出采集
- 超时控制

---

### 7. `yfai/mcp/` - MCP 层
**职责**: MCP 协议支持

**关键文件**:
- `registry.py` (200行): 服务器注册中心
- `client.py` (122行): MCP 客户端

**状态**: ⚠️ 部分实现
- ✅ HTTP 模拟
- ❌ WebSocket (待实现)

---

### 8. `yfai/automation/` - 自动化层
**职责**: 任务调度

**关键文件**:
- `scheduler.py` (178行): 调度器

**状态**: ⚠️ 部分实现
- ✅ Interval/Once 触发
- ❌ Cron 触发 (待实现)
- ❌ 文件/进程触发 (待实现)

---

### 9. `yfai/connectors/` - 连接器层
**职责**: 外部系统集成

**关键文件**:
- `base.py` (57行): 连接器基类
- `http.py` (66行): HTTP 连接器

**状态**: ⚠️ 部分实现
- ✅ HTTP 连接器
- ❌ Email/Git/Database (待实现)

---

## 🔄 数据流图

```
用户输入 (UI)
    ↓
MainWindow (app/main_window.py)
    ↓
ChatWidget (app/widgets/chat_widget.py)
    ↓
Orchestrator (core/orchestrator.py)
    ├─→ ProviderManager (providers/manager.py)
    │       ├─→ BailianProvider (providers/bailian.py)
    │       └─→ OllamaProvider (providers/ollama.py)
    │
    ├─→ SecurityGuard (security/guard.py)
    │       ├─→ SecurityPolicy (security/policy.py)
    │       └─→ ApprovalDialog (app/widgets/approval_dialog.py)
    │
    ├─→ LocalOps (localops/)
    │       ├─→ FileSystemOps (localops/fs.py)
    │       ├─→ ShellOps (localops/shell.py)
    │       ├─→ ProcessOps (localops/process.py)
    │       └─→ NetworkOps (localops/net.py)
    │
    ├─→ McpRegistry (mcp/registry.py)
    │       └─→ McpClient (mcp/client.py)
    │
    └─→ DatabaseManager (store/db.py)
            └─→ VectorIndexer (store/indexer.py)
```

---

## 📚 配置文件说明

### `configs/config.yaml`
主配置文件，包含:
- 应用配置 (default_provider, model_route 等)
- Provider 配置 (bailian, ollama)
- MCP 注册表
- 本地操作配置 (白名单、危险操作)
- 安全配置 (审批阈值、脱敏规则)
- RAG 配置 (embedding 模型、分块大小)
- 数据库配置
- UI 配置

### `configs/.env`
环境变量，包含:
- `DASHSCOPE_API_KEY`: 阿里百炼 API 密钥
- 其他敏感信息

**注意**: `.env` 文件不提交到 Git，使用 `.env.example` 作为模板

---

## 🗑️ 待删除文件 (old/ 目录)

### 原型文件
- `prototype/` - 14个 HTML 原型，已完成 PyQt6 实现

### 临时分析报告
- `CODE_ANALYSIS_REPORT.md` - 代码分析报告
- `CRITICAL_ISSUES_SUMMARY.md` - 关键问题汇总
- `ANALYSIS_QUICK_START.md` - 分析快速入门
- `ISSUES_CHECKLIST.csv` - 问题清单

### 临时优化文档
- `改造建设方案.md` - 重构方案
- `改造计划.md` - 实施计划
- `优化建议.md` - 优化建议

**建议**:
- 可以在 1-2 周后完全删除 `old/` 目录
- 或者将 `prototype/` 移到单独的分支保留

---

## 🎯 目录组织原则

### 1. 代码分层清晰
- **UI 层** (`app/`): 用户界面
- **核心层** (`core/`): 业务逻辑
- **数据层** (`store/`): 数据持久化
- **安全层** (`security/`): 权限控制
- **扩展层** (`providers/`, `mcp/`, `localops/`, `connectors/`, `automation/`): 可插拔模块

### 2. 文档分类明确
- **设计文档** (`docs/design/`): 架构、技术选型
- **开发文档** (`docs/development/`): 功能清单、问题列表
- **用户文档** (`docs/user-guide/`): 使用手册

### 3. 配置集中管理
- 所有配置文件在 `configs/` 目录
- 运行时文件不提交（`.gitignore`）
- 提供示例文件（`.example`）

### 4. 数据与代码分离
- 数据库文件在 `data/` 目录
- 日志文件在 `logs/` 目录
- 不提交到 Git

---

## 🔧 开发建议

### 1. 模块依赖关系
```
app (UI层)
  ↓ 依赖
core (核心层)
  ↓ 依赖
providers, security, localops, mcp, automation, connectors (扩展层)
  ↓ 依赖
store (数据层)
```

**原则**:
- 上层可以依赖下层
- 下层不应依赖上层
- 同层之间避免循环依赖

### 2. 新增模块指南

**添加新的 UI 页面**:
1. 在 `yfai/app/widgets/` 创建新文件
2. 继承 `QWidget`
3. 在 `main_window.py` 中注册
4. 在 `sidebar.py` 中添加导航

**添加新的 Provider**:
1. 在 `yfai/providers/` 创建新文件
2. 继承 `BaseProvider`
3. 实现 `chat()` 和 `stream_chat()` 方法
4. 在 `manager.py` 中注册

**添加新的工具**:
1. 在相应的 `localops/` 模块添加方法
2. 在 `orchestrator.py` 中注册工具路由
3. 在 `security/policy.py` 中配置风险等级

### 3. 测试建议

**目录结构**:
```
yfai/tests/
├── __init__.py
├── test_orchestrator.py
├── test_providers.py
├── test_security.py
├── test_localops.py
├── test_mcp.py
└── test_ui.py
```

**运行测试**:
```bash
pytest yfai/tests/ -v --cov=yfai
```

---

## 📖 相关文档

- **功能清单**: `FEATURES_STATUS.md` - 详细功能状态
- **开发路线图**: `DEVELOPMENT_ROADMAP.md` - 开发计划
- **项目总结**: `PROJECT_SUMMARY.md` - 项目完整总结
- **快速开始**: `QUICK_START.md` - 使用指南
- **安装说明**: `INSTALLATION.md` - 安装步骤

---

**维护者**: YFAI Team
**最后更新**: 2025-11-17
