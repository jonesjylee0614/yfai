# YFAI 安装指南

## 系统要求

### 必需
- **操作系统**: Windows 10/11, macOS 10.15+, Linux
- **Python**: 3.11 或更高版本
- **内存**: 至少 4GB RAM (推荐 8GB+)
- **磁盘**: 至少 500MB 可用空间

### 可选
- **Ollama**: 用于本地模型 (需额外5-10GB空间存储模型)

## 安装步骤

### 1. 克隆或下载项目

```bash
# 如果使用Git
git clone https://github.com/yourusername/yfai.git
cd yfai

# 或直接下载并解压项目文件
```

### 2. 创建虚拟环境 (推荐)

#### Windows (PowerShell)
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

#### macOS/Linux
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. 安装依赖

```bash
# 升级pip
python -m pip install --upgrade pip

# 安装项目依赖
pip install -r requirements.txt
```

**注意**: 安装过程可能需要几分钟,请耐心等待。

### 4. 配置项目

#### 4.1 复制配置文件

```bash
# Windows
Copy-Item configs\config.example.yaml configs\config.yaml

# macOS/Linux
cp configs/config.example.yaml configs/config.yaml
```

#### 4.2 配置API Key

创建 `configs/.env` 文件并添加:

```env
# 阿里百炼 API Key (必需)
DASHSCOPE_API_KEY=your_api_key_here
```

**获取百炼API Key:**
1. 访问 [阿里云百炼平台](https://dashscope.aliyun.com/)
2. 注册并登录
3. 在控制台获取API Key
4. 新用户通常有免费额度

#### 4.3 配置白名单 (可选)

编辑 `configs/config.yaml`,修改文件访问白名单:

```yaml
local_ops:
  roots_whitelist:
    - "D:/WorkSpace"              # 改为你的工作目录
    - "C:/Users/YourName/Desktop" # 改为你的桌面路径
```

### 5. 安装 Ollama (可选)

如果要使用本地模型:

#### Windows
1. 访问 [Ollama官网](https://ollama.ai/download)
2. 下载并安装Windows版本
3. 安装后Ollama会自动启动

#### macOS
```bash
brew install ollama
```

#### Linux
```bash
curl -fsSL https://ollama.ai/install.sh | sh
```

#### 拉取模型
```bash
# 推荐的编程模型
ollama pull qwen2.5-coder

# 通用对话模型
ollama pull llama3.1
```

## 验证安装

### 运行测试

```bash
python test_integration.py
```

你应该看到:
```
Total: 6/6 passed
```

### 启动应用

```bash
python run.py
```

如果看到主窗口打开,恭喜你,安装成功! 🎉

## 常见问题

### Q1: pip install 失败

**问题**: 提示某些包安装失败

**解决方案**:
```bash
# 使用国内镜像
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### Q2: PyQt6 安装失败

**问题**: PyQt6 安装出错

**解决方案**:
```bash
# 先安装依赖
pip install PyQt6-Qt6
pip install PyQt6-sip
pip install PyQt6
```

### Q3: faiss-cpu 安装失败

**问题**: faiss-cpu 在某些系统上安装失败

**解决方案**:
```bash
# 使用conda安装 (如果有conda)
conda install -c conda-forge faiss-cpu

# 或跳过faiss,暂时不使用向量检索功能
# (需要注释掉requirements.txt中的faiss-cpu)
```

### Q4: 运行时提示模块未找到

**问题**: `No module named 'xxx'`

**解决方案**:
```bash
# 确保虚拟环境已激活
# 重新安装依赖
pip install -r requirements.txt
```

### Q5: Ollama连接失败

**问题**: 无法连接到Ollama

**解决方案**:
1. 确认Ollama已安装并运行
2. 检查是否在11434端口运行: http://127.0.0.1:11434
3. 重启Ollama服务

### Q6: 百炼API调用失败

**问题**: 提示API Key无效或额度不足

**解决方案**:
1. 确认`.env`文件中的API Key正确
2. 登录百炼控制台检查额度
3. 确认API Key有调用权限

## 卸载

### 1. 删除虚拟环境

```bash
# Windows
Remove-Item -Recurse venv

# macOS/Linux
rm -rf venv
```

### 2. 删除数据

```bash
# 删除数据库和日志
Remove-Item -Recurse data, logs  # Windows
rm -rf data logs                  # macOS/Linux
```

### 3. 删除配置

```bash
Remove-Item configs\config.yaml, configs\.env  # Windows
rm configs/config.yaml configs/.env            # macOS/Linux
```

## 升级

### 更新依赖

```bash
# 拉取最新代码
git pull

# 更新依赖
pip install -r requirements.txt --upgrade
```

### 迁移数据库

```bash
# 备份现有数据库
Copy-Item data\yfai.db data\yfai.db.backup

# 如果有新的数据库迁移,运行:
# python -m yfai.store.migrate
```

## 技术支持

- 📖 查看 [QUICK_START.md](QUICK_START.md) 获取快速开始指南
- 📋 查看 [PROJECT_SUMMARY.md](PROJECT_SUMMARY.md) 了解项目详情  
- 🐛 报告问题: [GitHub Issues](https://github.com/yourusername/yfai/issues)

## 开发环境

如果你想参与开发:

```bash
# 安装开发依赖
pip install -r requirements.txt

# 安装代码检查工具
pip install ruff mypy pre-commit

# 设置pre-commit钩子
pre-commit install

# 运行代码检查
ruff check .
mypy yfai/
```

---

祝安装顺利! 如有问题,欢迎反馈。 🚀

