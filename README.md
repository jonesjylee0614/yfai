# YFAI - 本地对话式控制台

> **一个窗口，统一调用 AI & 工具 & 本机能力**

## 📋 项目简介

YFAI 是一个本地"对话式控制台"，统一接入百炼（DashScope）与本地 Ollama，作为 MCP Client 调用各类 MCP Server，并暴露一套可审计的本地控制能力（文件、进程、网络、脚本、窗口自动化等）。

## ✨ 核心特性

- 🤖 **多模型支持**: 统一接入阿里百炼和本地 Ollama
- 🔧 **MCP 集成**: 标准化工具调用协议，扩展性强
- 💻 **本地控制**: 安全的文件、进程、脚本、网络操作
- 🛡️ **安全审批**: 危险操作强制审批，完整审计日志
- 📚 **知识库 RAG**: 向量检索增强生成
- 🎯 **AI 助手**: 多专业助手管理
- 📊 **会话管理**: 完整的对话历史和检索
- ⌨️ **命令面板**: 快捷操作，提升效率

## 🚀 快速开始

### 环境要求

- Python 3.11+
- Windows 10/11 (推荐) / macOS / Linux

### 安装

```bash
# 使用 Poetry
poetry install

# 或使用 pip
pip install -r requirements.txt
```

### 配置

1. 复制配置示例文件：
```bash
cp configs/config.example.yaml configs/config.yaml
cp configs/.env.example configs/.env
```

2. 编辑 `configs/.env` 填入 API Key：
```env
DASHSCOPE_API_KEY=your_dashscope_api_key_here
```

3. 根据需要修改 `configs/config.yaml`

### 运行

```bash
# 使用 Poetry
poetry run yfai

# 或直接运行
python -m yfai.main
```

## 📁 项目结构

```
yfai/
├── app/                # PyQt6 桌面UI
│   ├── main_window.py  # 主窗口
│   ├── widgets/        # UI组件
│   └── resources/      # 资源文件
├── core/               # 核心调度逻辑
│   ├── orchestrator.py # 对话编排器
│   ├── router.py       # 消息路由
│   └── planner.py      # 任务规划
├── providers/          # LLM 提供商
│   ├── base.py         # 基础接口
│   ├── bailian.py      # 百炼适配器
│   └── ollama.py       # Ollama 适配器
├── mcp/                # MCP 客户端
│   ├── client.py       # MCP 客户端
│   └── registry.py     # 注册中心
├── localops/           # 本地操作能力
│   ├── fs.py           # 文件系统
│   ├── shell.py        # Shell 执行
│   ├── process.py      # 进程管理
│   └── net.py          # 网络工具
├── security/           # 安全模块
│   ├── guard.py        # 权限守卫
│   └── policy.py       # 策略管理
├── store/              # 数据存储
│   ├── db.py           # 数据库
│   └── indexer.py      # 向量索引
├── configs/            # 配置文件
│   ├── config.yaml     # 主配置
│   └── .env            # 环境变量
├── scripts/            # 脚本模板
├── tests/              # 测试
└── main.py             # 程序入口
```

## 🎯 核心功能

### 1. AI 对话

- 流式对话输出
- 多模型切换（百炼/Ollama）
- 上下文管理
- 命令模式支持

### 2. AI 助手管理

- 创建专业助手
- 预设提示词模板
- 使用统计
- 助手配置

### 3. 会话管理

- 完整历史记录
- 时间分组展示
- 会话搜索
- 导出功能

### 4. 知识库 RAG

- 多数据源支持
- 向量检索
- 相似度搜索
- 实时索引

### 5. MCP 工具集成

- 标准化工具调用
- 工具注册发现
- 健康检查
- 状态监控

### 6. 本地控制能力

- 文件操作（读/写/搜索）
- Shell 脚本执行
- 进程管理
- 网络工具
- 剪贴板操作
- UI 自动化（可选）

### 7. 安全审批

- 危险操作审批
- 风险等级识别
- 操作审计日志
- 权限白名单

## 🔒 安全特性

- ✅ 默认只读，危险操作需审批
- ✅ 完整的审计日志
- ✅ 敏感信息脱敏
- ✅ 操作白名单机制
- ✅ 超时和熔断保护

## 📚 文档

- [设计文档](docs/设计文档.md)
- [技术栈与实现规划](docs/技术栈与实现规划.md)
- [原型说明](prototype/README.md)
- [功能特性](prototype/FEATURES.md)
- [路线图](prototype/ROADMAP.md)

## 🛠️ 开发

### 运行测试

```bash
pytest tests/
```

### 代码检查

```bash
# Ruff 检查
ruff check .

# MyPy 类型检查
mypy yfai/
```

### 格式化代码

```bash
ruff format .
```

## 📝 TODO

- [x] 项目基础结构
- [x] 配置管理
- [x] 数据库模型
- [x] Provider 抽象
- [x] MCP 客户端
- [x] 本地控制模块
- [x] 核心调度器
- [x] 安全审批
- [x] PyQt6 UI
- [ ] 完整测试覆盖
- [ ] 文档完善
- [ ] 打包发布

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

MIT License

## 👥 团队

YFAI Development Team

---

**注意**: 本项目处于积极开发中，API 可能会有变动。

