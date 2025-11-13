# YFAI 快速开始指南

## 📦 安装依赖

### 方式一: 使用 pip (推荐)

```bash
# 安装依赖
pip install -r requirements.txt
```

### 方式二: 使用 Poetry

```bash
# 安装 Poetry (如果没有)
pip install poetry

# 安装依赖
poetry install
```

## ⚙️ 配置

### 1. 复制配置文件

```bash
# Windows PowerShell
Copy-Item configs\config.example.yaml configs\config.yaml

# Linux/macOS
cp configs/config.example.yaml configs/config.yaml
```

### 2. 配置环境变量

创建 `configs/.env` 文件:

```env
# 阿里百炼 API Key (必需)
DASHSCOPE_API_KEY=your_dashscope_api_key_here

# 其他可选配置
# MCP_TOKEN=your_mcp_token
```

**获取百炼API Key:**
1. 访问 [阿里云百炼平台](https://dashscope.aliyun.com/)
2. 注册/登录账号
3. 进入控制台获取API Key

### 3. 配置 Ollama (可选)

如果要使用本地Ollama模型:

1. 安装 Ollama: https://ollama.ai/
2. 拉取模型:
   ```bash
   ollama pull qwen2.5-coder
   ollama pull llama3.1
   ```
3. 确保Ollama服务运行在 `http://127.0.0.1:11434`

## 🚀 运行

### 方式一: 直接运行 (推荐)

```bash
python run.py
```

### 方式二: 作为模块运行

```bash
python -m yfai
```

### 方式三: 使用 Poetry

```bash
poetry run yfai
```

## 🎯 快速体验

### 1. 首次启动

启动后你会看到:
- 左侧: 导航栏 (对话/助手/会话/知识库/工具/日志/设置)
- 中间: 对话界面
- 右侧: 工具面板 (可通过 Ctrl+T 切换)

### 2. 开始对话

在输入框输入消息,例如:
```
你好,请介绍一下你自己
```

按 Enter 发送 (Shift+Enter 换行)

### 3. 切换模型

在顶部工具栏可以切换:
- 百炼(DashScope) - 在线模型,功能强大
- Ollama - 本地模型,隐私保护
- 自动 - 根据任务自动选择

### 4. 使用工具

点击右上角工具按钮或按 Ctrl+T 打开工具面板,可以:
- 📁 读写文件
- ⚡ 执行Shell命令
- 🔧 管理进程
- 🌐 发送HTTP请求

**注意**: 危险操作(删除/终止进程等)会弹出审批确认。

### 5. 快捷键

- `Ctrl+N` - 新建对话
- `Ctrl+T` - 切换工具面板
- `Ctrl+,` - 打开设置
- `Ctrl+Q` - 退出应用
- `Enter` - 发送消息
- `Shift+Enter` - 换行

## 📊 功能说明

### 对话功能
- ✅ 流式输出
- ✅ 消息历史
- ✅ 多会话管理
- ✅ 上下文记忆

### 安全机制
- ✅ 操作白名单
- ✅ 风险等级评估
- ✅ 审批流程
- ✅ 审计日志
- ✅ 敏感信息脱敏

### 本地控制
- ✅ 文件读写
- ✅ Shell执行
- ✅ 进程管理
- ✅ 网络工具

## 🔧 故障排除

### 1. 启动失败

**问题**: 提示缺少依赖
**解决**: 重新安装依赖
```bash
pip install -r requirements.txt
```

### 2. 配置文件错误

**问题**: 提示配置文件不存在
**解决**: 确保复制了配置文件
```bash
Copy-Item configs\config.example.yaml configs\config.yaml
```

### 3. API Key 无效

**问题**: 百炼调用失败
**解决**: 
1. 检查 `configs/.env` 中的 DASHSCOPE_API_KEY
2. 确保API Key有效且有足够额度

### 4. Ollama 连接失败

**问题**: 无法连接到Ollama
**解决**:
1. 确保Ollama已安装并运行
2. 检查端口是否为 11434
3. 拉取所需模型: `ollama pull qwen2.5-coder`

### 5. 数据库错误

**问题**: 数据库相关错误
**解决**: 删除并重新初始化数据库
```bash
# Windows
Remove-Item data\yfai.db
python run.py

# Linux/macOS
rm data/yfai.db
python run.py
```

## 📚 进阶使用

### 自定义配置

编辑 `configs/config.yaml`:

```yaml
# 修改默认Provider
app:
  default_provider: ollama  # bailian / ollama / auto

# 修改文件访问白名单
local_ops:
  roots_whitelist:
    - "D:/YourWorkspace"
    - "C:/YourDocuments"

# 修改安全阈值
security:
  confirm_threshold: high  # low / medium / high / critical
```

### 添加MCP服务器

编辑 `configs/McpRegistry.yaml`:

```yaml
servers:
  - id: my-mcp-server
    name: "我的MCP服务器"
    type: local
    endpoint: ws://127.0.0.1:9000
    enabled: true
```

## 🆘 获取帮助

- 查看文档: `docs/` 目录
- 查看原型: `prototype/` 目录
- 查看变更日志: `CHANGELOG.md`

## 🎉 开始使用

现在你已经准备好了!尽情探索YFAI的强大功能吧!

```bash
python run.py
```

祝使用愉快! 🚀

