# 更新日志

## [0.2.0] - 2025-11-13

### 新增 - Phase 1-5 完整实现
- ✨ **智能体系统 (Phase 1)**
  - Agent 数据模型(名称、描述、系统提示词、默认模型、允许工具、最大步骤数)
  - AgentRunner 核心逻辑(计划生成、步骤执行、结果记录)
  - JobRun 和 JobStep 表(任务运行记录和步骤追踪)
  - 智能体管理 UI(列表、创建、编辑、运行)
  - 内置智能体(DevOps 助手、知识整理助手、系统巡检助手)
  - 智能体与 Orchestrator 集成

- ✨ **自动化调度系统 (Phase 2)**
  - AutomationTask 数据模型(任务名称、触发类型、调度配置)
  - AutomationScheduler 调度器(间隔调度、Cron 调度、一次性任务)
  - 支持多种触发器(cron、interval、once、file、process、webhook)
  - 任务状态跟踪(最后运行时间、运行次数、状态)
  - 手动触发任务功能

- ✨ **连接器框架 (Phase 3)**
  - Connector 数据模型(名称、类型、配置、状态)
  - BaseConnector 抽象基类
  - HttpConnector 实现(支持 GET/POST/PUT/DELETE)
  - 连接测试和状态管理

- ✨ **运行观测增强 (Phase 4)**
  - JobRun 详情页面(基本信息、执行步骤、耗时统计)
  - JobStep 详细展示(步骤索引、类型、名称、状态、耗时)
  - 审批决策记录(仅此一次/永久允许/拒绝)
  - 执行总结和错误信息展示

- ✨ **UI 增强**
  - 侧边栏新增入口(智能体、运行记录、连接器、自动化)
  - 智能体管理页面(创建、编辑、列表、运行)
  - 运行记录页面(Job 列表、详情查看)
  - 完整的 Agent 配置对话框

### 改进
- 🔧 数据库扩展支持新表(agents、job_runs、job_steps、automation_tasks、connectors)
- 🔧 Orchestrator 集成 AgentRunner
- 🔧 数据库统计信息增加新表计数

### 技术架构
- **智能体层**: Agent + AgentRunner + JobRun/JobStep
- **自动化层**: AutomationScheduler + AutomationTask
- **连接器层**: BaseConnector + HttpConnector
- **数据层**: SQLAlchemy ORM + 新增5张表
- **UI层**: PyQt6 + 新增页面组件

## [0.1.0] - 2025-11-12

### 新增
- ✨ 完整的项目基础架构
- ✨ 数据库模型(SQLite)
  - 会话管理
  - 消息历史
  - 工具调用记录
  - AI助手配置
  - 知识库管理
- ✨ Provider抽象层
  - 阿里百炼(DashScope)适配器
  - Ollama本地模型适配器
  - 统一的聊天接口
  - 流式输出支持
  - 健康检查和降级机制
- ✨ MCP客户端
  - MCP服务器注册中心
  - 工具列表和调用
  - 权限管理
- ✨ 本地控制能力
  - 文件系统操作(读/写/列表/删除/搜索)
  - Shell脚本执行(PowerShell/Bash/CMD)
  - 进程管理(列表/查询/终止)
  - 网络工具(HTTP请求/端口检查/DNS解析)
- ✨ 安全模块
  - 操作审批流程
  - 风险等级评估
  - 审计日志
  - 敏感信息脱敏
  - 权限白名单
- ✨ 核心调度器
  - 对话编排
  - 会话管理
  - 工具路由
  - 消息历史
- ✨ PyQt6桌面UI
  - 主对话界面
  - 侧边栏导航
  - 工具面板
  - 设置对话框
  - 异步消息循环
  - 流式对话显示

### 技术栈
- Python 3.11+
- PyQt6 - 桌面UI
- SQLAlchemy - 数据库ORM
- httpx - HTTP客户端
- faiss - 向量索引
- pydantic - 数据验证
- qasync - Qt异步支持

### 已知问题
- 向量检索功能需要进一步完善
- MCP客户端目前使用HTTP模拟,需要实现WebSocket
- UI组件需要更多交互细节
- 缺少完整的测试覆盖

### 待开发
- [ ] AI助手管理UI
- [ ] 会话历史UI
- [ ] 知识库RAG UI
- [ ] 审批弹窗
- [ ] 命令面板
- [ ] 日志查看器
- [ ] 更多本地工具
- [ ] 插件系统
- [ ] 多窗口支持
- [ ] 完整的测试

## 开发团队
YFAI Development Team

## 许可证
MIT License

