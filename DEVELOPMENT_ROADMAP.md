# YFAI 开发功能清单与路线图

> 基于全面代码审查生成
> 生成日期: 2025-11-17
> 分析范围: 49个Python文件，1.3MB代码

---

## 📊 总体概览

### 当前状态统计
- ✅ **已完成核心功能**: 13个
- ⚠️ **部分实现/需完善**: 8个
- ❌ **未实现/待开发**: 12个
- 🐛 **已发现问题**: 47个（20高/19中/8低）

### 开发优先级分布
| 优先级 | 数量 | 时间估算 | 说明 |
|--------|------|---------|------|
| P0 (紧急) | 7个 | 1-2周 | 影响核心功能，必须立即修复 |
| P1 (高) | 18个 | 2-4周 | 重要功能缺失或严重bug |
| P2 (中) | 22个 | 1-2月 | 功能增强和优化 |
| P3 (低) | 8个 | 2-3月 | 体验优化和边缘功能 |

---

## 🎯 Phase 1: 紧急修复（P0，1-2周）

### 1.1 核心功能Bug修复

#### 🔴 1. 流式聊天数据丢失问题
**优先级**: P0 | **估时**: 2-3天 | **难度**: ⭐⭐⭐

**文件**: `yfai/core/orchestrator.py:156-220`

**问题描述**:
- 流式输出过程中如果发生异常，已发送给用户的内容不会保存到数据库
- 导致用户看到的内容与历史记录不一致

**实现方案**:
```python
# 方案1: 缓冲区机制（推荐）
async def stream_chat(...):
    full_response = ""
    buffer_size = 100  # 每100字符保存一次

    try:
        async for chunk in provider_obj.stream_chat(...):
            full_response += chunk
            yield chunk

            # 定期保存检查点
            if len(full_response) % buffer_size < len(chunk):
                await self._save_partial_message(session_id, full_response)

        # 最终保存完整消息
        await self._finalize_message(session_id, full_response)
    except Exception as e:
        # 保存已接收的部分
        await self._save_partial_message(session_id, full_response, error=str(e))
        raise

# 方案2: 数据库临时表
# 在 Message 表中添加 status 字段 (pending/completed/error)
```

**验收标准**:
- [ ] 异常情况下部分内容能保存
- [ ] 用户历史记录与实际看到内容一致
- [ ] 添加单元测试覆盖异常场景

---

#### 🔴 2. 异步回调函数混乱
**优先级**: P0 | **估时**: 1天 | **难度**: ⭐⭐

**文件**: `yfai/security/guard.py:163`, `yfai/core/agent_runner.py:389`

**问题描述**:
- `approval_callback` 可能是同步或异步函数
- 当前代码未检测，导致审批流程失效

**实现方案**:
```python
import inspect
from typing import Union, Callable, Awaitable

# guard.py 修复
async def request_approval(self, request: ApprovalRequest) -> ApprovalResult:
    if not self.approval_callback:
        return ApprovalResult(status=ApprovalStatus.TIMEOUT, message="No callback")

    try:
        if inspect.iscoroutinefunction(self.approval_callback):
            result = await self.approval_callback(request)
        else:
            result = self.approval_callback(request)
        return result
    except Exception as e:
        logger.error(f"Approval callback failed: {e}")
        return ApprovalResult(status=ApprovalStatus.REJECTED, message=f"Error: {e}")
```

**验收标准**:
- [ ] 支持同步和异步回调
- [ ] 添加类型注解
- [ ] 异常情况自动拒绝并记录日志

---

#### 🔴 3. Provider响应解析崩溃
**优先级**: P0 | **估时**: 1天 | **难度**: ⭐⭐

**文件**: `yfai/providers/bailian.py:81-91`, `yfai/providers/ollama.py:66-79`

**问题描述**:
- 未检查API响应结构，数组越界和None访问导致崩溃

**实现方案**:
```python
# bailian.py 修复
async def chat(self, messages, model=None, stream=False):
    try:
        response = await self.client.call(...)
        result = json.loads(response.output.text)

        # 验证响应结构
        if not isinstance(result, dict):
            raise ValueError(f"Invalid response type: {type(result)}")

        choices = result.get("choices", [])
        if not choices or len(choices) == 0:
            raise ValueError("Empty choices in response")

        choice = choices[0]
        message_content = choice.get("message", {})

        if not isinstance(message_content, dict):
            raise ValueError(f"Invalid message type: {type(message_content)}")

        content = message_content.get("content", "")

        return ChatResponse(
            content=content,
            model=model or self.default_model,
            provider="bailian",
        )
    except Exception as e:
        logger.error(f"Bailian chat failed: {e}", exc_info=True)
        # 返回错误响应而不是崩溃
        return ChatResponse(
            content=f"[错误] {str(e)}",
            model=model or self.default_model,
            provider="bailian",
        )

# ollama.py 类似修复
```

**验收标准**:
- [ ] 所有字段访问前验证类型
- [ ] 异常情况返回错误提示而非崩溃
- [ ] 添加详细日志
- [ ] 单元测试覆盖异常格式

---

#### 🔴 4. UI操作无保护
**优先级**: P0 | **估时**: 1天 | **难度**: ⭐⭐

**文件**: `yfai/app/widgets/chat_widget.py:185,168-196`

**问题描述**:
- `findChild()` 返回None时未检查
- 流式输出循环中任何异常都会导致崩溃

**实现方案**:
```python
# chat_widget.py 修复
async def _handle_send(self):
    try:
        user_message = self.input_box.toPlainText().strip()
        if not user_message:
            return

        # 创建气泡
        assistant_bubble = self._create_assistant_bubble()
        assistant_label = assistant_bubble.findChild(QLabel)

        if not assistant_label:
            logger.error("Failed to create assistant label")
            self._show_error("界面错误：无法创建消息气泡")
            return

        full_response = ""

        try:
            async for chunk in self.orchestrator.stream_chat(...):
                full_response += chunk
                assistant_label.setText(full_response)
                QApplication.processEvents()
        except asyncio.CancelledError:
            logger.info("Chat cancelled by user")
            assistant_label.setText(full_response + "\n[已取消]")
        except Exception as e:
            logger.error(f"Stream chat error: {e}", exc_info=True)
            assistant_label.setText(full_response + f"\n[错误: {e}]")
            self._show_error(f"聊天失败: {e}")

    except Exception as e:
        logger.error(f"Chat handler error: {e}", exc_info=True)
        self._show_error(f"发送消息失败: {e}")

def _show_error(self, message: str):
    """显示错误提示"""
    QMessageBox.warning(self, "错误", message)
```

**验收标准**:
- [ ] 所有UI查找操作都有None检查
- [ ] 异常情况显示友好错误提示
- [ ] 用户可以取消流式输出
- [ ] 添加日志记录

---

#### 🔴 5. 数据库事务异常处理
**优先级**: P0 | **估时**: 2天 | **难度**: ⭐⭐⭐

**文件**: 多个文件（orchestrator.py, agent_runner.py等）

**问题描述**:
- commit() 失败未回滚
- 异常时状态不一致

**实现方案**:
```python
# 创建数据库操作辅助装饰器
def safe_db_operation(rollback_on_error=True):
    def decorator(func):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            with self.db_manager.get_session() as db_session:
                try:
                    result = await func(self, db_session, *args, **kwargs)
                    db_session.commit()
                    return result
                except Exception as e:
                    if rollback_on_error:
                        db_session.rollback()
                    logger.error(f"Database operation failed in {func.__name__}: {e}", exc_info=True)
                    raise
        return wrapper
    return decorator

# 使用示例
@safe_db_operation()
async def create_session(self, db_session, title, assistant_id, knowledge_base_id):
    session_id = str(uuid.uuid4())
    session = Session(...)
    db_session.add(session)
    return session_id
```

**验收标准**:
- [ ] 所有数据库操作都有try-catch
- [ ] 失败自动回滚
- [ ] 添加重试机制（可选）
- [ ] 记录详细日志

---

#### 🔴 6. Agent统计更新非原子性
**优先级**: P0 | **估时**: 1天 | **难度**: ⭐⭐

**文件**: `yfai/core/agent_runner.py:78-81`

**问题描述**:
- 并发调用同一Agent时，usage_count更新可能丢失

**实现方案**:
```python
# 使用数据库级别的原子更新
with self.db.get_session() as db_session:
    # 方案1: 使用 UPDATE ... SET count = count + 1
    db_session.query(Agent).filter_by(id=agent_id).update({
        "usage_count": Agent.usage_count + 1,
        "last_used_at": datetime.utcnow()
    }, synchronize_session=False)
    db_session.commit()

    # 方案2: 使用数据库锁
    agent = db_session.query(Agent).filter_by(id=agent_id).with_for_update().first()
    agent.usage_count += 1
    agent.last_used_at = datetime.utcnow()
    db_session.commit()
```

**验收标准**:
- [ ] 并发测试不丢失计数
- [ ] 性能无明显下降
- [ ] 添加并发测试用例

---

#### 🔴 7. 审计日志实现
**优先级**: P0 | **估时**: 2-3天 | **难度**: ⭐⭐⭐

**文件**: `yfai/security/guard.py:188`

**问题描述**:
- 代码中有 `# TODO: 写入数据库` 标记
- 审批决策未持久化

**实现方案**:
```python
# 1. 创建审计日志表
# db.py 添加新模型
class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    action_type = Column(String(50))  # approval_request, approval_result, tool_call, etc.
    user_id = Column(String(36))
    tool_name = Column(String(100))
    risk_level = Column(String(20))
    approval_status = Column(String(20))  # approved, rejected, timeout
    request_data = Column(Text)  # JSON
    result_data = Column(Text)  # JSON
    ip_address = Column(String(50))
    session_id = Column(String(36))

# 2. guard.py 实现
def _log_approval_decision(self, request: ApprovalRequest, result: ApprovalResult):
    try:
        with self.db_manager.get_session() as db_session:
            audit_log = AuditLog(
                id=str(uuid.uuid4()),
                action_type="approval_decision",
                tool_name=request.tool_name,
                risk_level=request.risk_level.value,
                approval_status=result.status.value,
                request_data=json.dumps({
                    "params": request.params,
                    "context": request.context
                }, ensure_ascii=False),
                result_data=json.dumps({
                    "message": result.message,
                    "decision_time": result.decision_time
                }, ensure_ascii=False),
                session_id=request.session_id
            )
            db_session.add(audit_log)
            db_session.commit()
    except Exception as e:
        logger.error(f"Failed to write audit log: {e}")
        # 审计日志失败不应影响主流程

# 3. 在 request_approval 中调用
async def request_approval(...):
    # ... 现有逻辑 ...
    self._log_approval_decision(request, result)
    return result
```

**验收标准**:
- [ ] 所有审批决策都记录
- [ ] 包含完整上下文信息
- [ ] 提供查询接口
- [ ] UI展示审计日志（可选）

---

## 🔧 Phase 2: 重要功能完善（P1，2-4周）

### 2.1 未完成功能实现

#### ⚠️ 8. MCP客户端WebSocket支持
**优先级**: P1 | **估时**: 3-4天 | **难度**: ⭐⭐⭐⭐

**文件**: `yfai/mcp/client.py`

**问题描述**:
- 当前只有HTTP模拟实现
- 注释说明需要WebSocket

**实现方案**:
```python
import websockets
import asyncio

class McpClient:
    def __init__(self, endpoint: str, auth_token: Optional[str] = None, timeout: int = 30):
        self.endpoint = endpoint
        self.auth_token = auth_token
        self.timeout = timeout
        self.ws = None
        self.session_id = None
        self._response_futures = {}  # 用于匹配请求和响应

    async def connect(self) -> bool:
        """使用WebSocket连接"""
        try:
            headers = {}
            if self.auth_token:
                headers["Authorization"] = f"Bearer {self.auth_token}"

            self.ws = await websockets.connect(
                self.endpoint,
                extra_headers=headers,
                ping_interval=30,
                ping_timeout=10
            )

            # 发送初始化消息
            await self._send_message({
                "type": "initialize",
                "version": "1.0"
            })

            # 启动接收循环
            asyncio.create_task(self._receive_loop())

            return True
        except Exception as e:
            logger.error(f"MCP connection failed: {e}")
            return False

    async def _receive_loop(self):
        """接收消息循环"""
        try:
            async for message in self.ws:
                data = json.loads(message)
                request_id = data.get("request_id")

                if request_id and request_id in self._response_futures:
                    future = self._response_futures.pop(request_id)
                    future.set_result(data)
        except Exception as e:
            logger.error(f"MCP receive loop error: {e}")

    async def call_tool(self, tool_name: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """通过WebSocket调用工具"""
        request_id = str(uuid.uuid4())
        future = asyncio.Future()
        self._response_futures[request_id] = future

        try:
            await self._send_message({
                "type": "tool_call",
                "request_id": request_id,
                "tool": tool_name,
                "params": params
            })

            # 等待响应（带超时）
            response = await asyncio.wait_for(future, timeout=self.timeout)
            return response
        except asyncio.TimeoutError:
            logger.error(f"Tool call timeout: {tool_name}")
            self._response_futures.pop(request_id, None)
            return None
        except Exception as e:
            logger.error(f"Tool call failed: {e}")
            return None
```

**验收标准**:
- [ ] 支持WebSocket连接
- [ ] 自动重连机制
- [ ] 心跳保活
- [ ] 向后兼容HTTP模式
- [ ] 完整的错误处理

---

#### ⚠️ 9. Cron调度器完整实现
**优先级**: P1 | **估时**: 2-3天 | **难度**: ⭐⭐⭐

**文件**: `yfai/automation/scheduler.py:92-93,118-121`

**问题描述**:
- Cron调度只有占位实现
- `_check_and_trigger_tasks` 是空函数

**实现方案**:
```python
from croniter import croniter
from datetime import datetime, timedelta

class AutomationScheduler:
    def __init__(self, ...):
        # ... 现有代码 ...
        self.cron_tasks: Dict[str, Dict] = {}  # task_id -> {next_run, cron_expr}

    async def _schedule_task(self, task: Dict[str, Any]):
        task_id = task["id"]
        trigger_type = task["trigger_type"]

        if trigger_type == "cron":
            cron_expr = task.get("cron_expr")
            if not cron_expr:
                logger.error(f"Task {task_id} missing cron_expr")
                return

            try:
                # 验证cron表达式
                cron = croniter(cron_expr, datetime.now())
                next_run = cron.get_next(datetime)

                self.cron_tasks[task_id] = {
                    "next_run": next_run,
                    "cron_expr": cron_expr,
                    "task": task
                }

                logger.info(f"Cron task {task_id} scheduled, next run: {next_run}")
            except Exception as e:
                logger.error(f"Invalid cron expression for task {task_id}: {e}")

    async def _check_and_trigger_tasks(self):
        """检查并触发Cron任务"""
        now = datetime.now()

        for task_id, cron_data in list(self.cron_tasks.items()):
            next_run = cron_data["next_run"]

            if now >= next_run:
                # 执行任务
                logger.info(f"Triggering cron task: {task_id}")
                asyncio.create_task(self._execute_automation_task(task_id))

                # 计算下次运行时间
                cron = croniter(cron_data["cron_expr"], now)
                next_run = cron.get_next(datetime)
                cron_data["next_run"] = next_run

                logger.info(f"Next run for {task_id}: {next_run}")
```

**依赖**:
```bash
pip install croniter
```

**验收标准**:
- [ ] 支持标准Cron表达式
- [ ] 准时触发（误差<1分钟）
- [ ] 自动计算下次运行时间
- [ ] 任务执行失败不影响调度
- [ ] 单元测试覆盖

---

#### ⚠️ 10. 文件/进程事件触发器
**优先级**: P1 | **估时**: 3-4天 | **难度**: ⭐⭐⭐⭐

**文件**: `yfai/automation/scheduler.py`

**功能描述**:
- 文件变化触发（watchdog）
- 进程状态触发（psutil）

**实现方案**:
```python
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import psutil

class FileEventHandler(FileSystemEventHandler):
    def __init__(self, scheduler, task_id):
        self.scheduler = scheduler
        self.task_id = task_id

    def on_modified(self, event):
        if not event.is_directory:
            logger.info(f"File modified: {event.src_path}, triggering task {self.task_id}")
            asyncio.create_task(self.scheduler._execute_automation_task(self.task_id))

class AutomationScheduler:
    def __init__(self, ...):
        # ... 现有代码 ...
        self.file_observers = {}
        self.process_monitors = {}

    async def _schedule_task(self, task: Dict[str, Any]):
        # ... 现有代码 ...

        elif trigger_type == "file":
            # 文件监听
            watch_path = task.get("watch_path")
            pattern = task.get("file_pattern", "*")

            if not watch_path or not os.path.exists(watch_path):
                logger.error(f"Invalid watch path for task {task_id}")
                return

            event_handler = FileEventHandler(self, task_id)
            observer = Observer()
            observer.schedule(event_handler, watch_path, recursive=True)
            observer.start()

            self.file_observers[task_id] = observer
            logger.info(f"File monitor started for {task_id}: {watch_path}")

        elif trigger_type == "process":
            # 进程监控
            process_name = task.get("process_name")
            check_interval = task.get("check_interval", 60)
            trigger_on = task.get("trigger_on", "exit")  # start, exit, cpu_high, mem_high

            asyncio.create_task(self._monitor_process(task_id, process_name, trigger_on, check_interval))

    async def _monitor_process(self, task_id, process_name, trigger_on, interval):
        """监控进程状态"""
        last_state = None

        while self.running:
            try:
                # 查找进程
                processes = [p for p in psutil.process_iter(['name']) if p.info['name'] == process_name]
                current_state = len(processes) > 0

                # 检查触发条件
                should_trigger = False
                if trigger_on == "start" and current_state and not last_state:
                    should_trigger = True
                elif trigger_on == "exit" and not current_state and last_state:
                    should_trigger = True

                if should_trigger:
                    logger.info(f"Process trigger: {process_name} {trigger_on}")
                    await self._execute_automation_task(task_id)

                last_state = current_state
                await asyncio.sleep(interval)

            except Exception as e:
                logger.error(f"Process monitor error: {e}")
                await asyncio.sleep(interval)
```

**验收标准**:
- [ ] 文件创建/修改/删除触发
- [ ] 进程启动/退出触发
- [ ] 进程CPU/内存阈值触发
- [ ] 资源正确清理
- [ ] 性能影响可控

---

#### ⚠️ 11. Connector实现（Email, Git）
**优先级**: P1 | **估时**: 5-7天 | **难度**: ⭐⭐⭐⭐

**文件**: `yfai/connectors/`（新建）

**功能描述**:
- Email连接器（发送/接收邮件）
- Git连接器（克隆/提交/推送）

**实现方案**:
```python
# email_connector.py
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import imaplib
import email

class EmailConnector(BaseConnector):
    """Email 连接器"""

    async def connect(self) -> bool:
        try:
            smtp_host = self.config.get("smtp_host")
            smtp_port = self.config.get("smtp_port", 587)
            username = self.config.get("username")
            password = self.config.get("password")

            self.smtp = smtplib.SMTP(smtp_host, smtp_port)
            self.smtp.starttls()
            self.smtp.login(username, password)

            self.connected = True
            return True
        except Exception as e:
            logger.error(f"Email connection failed: {e}")
            return False

    async def call(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        if action == "send":
            return await self._send_email(params)
        elif action == "fetch":
            return await self._fetch_emails(params)
        else:
            return {"success": False, "error": f"Unknown action: {action}"}

    async def _send_email(self, params: Dict[str, Any]) -> Dict[str, Any]:
        try:
            msg = MIMEMultipart()
            msg['From'] = params.get("from")
            msg['To'] = params.get("to")
            msg['Subject'] = params.get("subject")

            body = params.get("body", "")
            msg.attach(MIMEText(body, 'plain'))

            self.smtp.send_message(msg)

            return {"success": True, "message": "Email sent"}
        except Exception as e:
            return {"success": False, "error": str(e)}

# git_connector.py
import git

class GitConnector(BaseConnector):
    """Git 连接器"""

    async def call(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        if action == "clone":
            return await self._clone_repo(params)
        elif action == "commit":
            return await self._commit(params)
        elif action == "push":
            return await self._push(params)
        # ... 更多操作

    async def _clone_repo(self, params: Dict[str, Any]) -> Dict[str, Any]:
        try:
            repo_url = params.get("url")
            dest_path = params.get("path")

            git.Repo.clone_from(repo_url, dest_path)

            return {"success": True, "path": dest_path}
        except Exception as e:
            return {"success": False, "error": str(e)}
```

**验收标准**:
- [ ] Email发送/接收功能
- [ ] Git基本操作（clone/commit/push/pull）
- [ ] 配置加密存储
- [ ] 连接测试功能
- [ ] UI集成

---

#### ⚠️ 12. 日志页面数据加载
**优先级**: P1 | **估时**: 1-2天 | **难度**: ⭐⭐

**文件**: `yfai/app/widgets/logs_page.py:87,166,179`

**问题描述**:
- 有3个TODO标记
- 日志加载/筛选/清空未实现

**实现方案**:
```python
# logs_page.py

def _load_logs(self):
    """从数据库加载日志"""
    self.log_list.clear()

    try:
        # 从ToolCall表加载工具调用日志
        with self.orchestrator.db_manager.get_session() as db_session:
            from yfai.store.db import ToolCall, AuditLog

            # 构建查询
            query = db_session.query(ToolCall).order_by(ToolCall.created_at.desc())

            # 应用筛选
            if self.level_filter.currentText() != "全部":
                level_map = {"错误": "failed", "成功": "success", "待审批": "pending"}
                query = query.filter(ToolCall.status == level_map[self.level_filter.currentText()])

            if self.source_filter.currentText() != "全部":
                query = query.filter(ToolCall.tool_name.like(f"{self.source_filter.currentText()}%"))

            # 限制数量
            logs = query.limit(1000).all()

            for log in logs:
                # 格式化时间
                timestamp = log.created_at.strftime("%Y-%m-%d %H:%M:%S")

                # 状态图标
                status_icon = {
                    "success": "✅",
                    "failed": "❌",
                    "pending": "⏳"
                }.get(log.status, "❓")

                # 添加到列表
                item = QListWidgetItem(
                    f"{status_icon} [{timestamp}] {log.tool_name} - {log.status}"
                )
                item.setData(Qt.ItemDataRole.UserRole, log.to_dict())
                self.log_list.addItem(item)

    except Exception as e:
        logger.error(f"Failed to load logs: {e}")
        QMessageBox.warning(self, "错误", f"加载日志失败: {e}")

def _apply_filter(self):
    """应用筛选条件"""
    self._load_logs()  # 重新加载并应用筛选

def _clear_logs(self):
    """清空日志"""
    reply = QMessageBox.question(
        self,
        "确认",
        "确定要清空所有日志吗？此操作不可恢复。",
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
    )

    if reply == QMessageBox.StandardButton.Yes:
        try:
            with self.orchestrator.db_manager.get_session() as db_session:
                from yfai.store.db import ToolCall

                # 删除所有记录（可选：只删除旧记录）
                cutoff_date = datetime.utcnow() - timedelta(days=90)
                db_session.query(ToolCall).filter(ToolCall.created_at < cutoff_date).delete()
                db_session.commit()

            self._load_logs()
            QMessageBox.information(self, "成功", "日志已清空")

        except Exception as e:
            logger.error(f"Failed to clear logs: {e}")
            QMessageBox.warning(self, "错误", f"清空日志失败: {e}")
```

**验收标准**:
- [ ] 显示所有工具调用记录
- [ ] 按级别/时间/来源筛选
- [ ] 查看详细日志
- [ ] 导出日志功能
- [ ] 清空旧日志

---

#### ⚠️ 13. 知识库构建流程
**优先级**: P1 | **估时**: 4-5天 | **难度**: ⭐⭐⭐⭐

**文件**: `yfai/app/widgets/knowledge_page.py`, `yfai/store/indexer.py`

**功能描述**:
- 完整的知识库构建流程
- 文档扫描、分块、向量化、索引

**实现方案**:
```python
# knowledge_builder.py (新建)
from pathlib import Path
import hashlib
from typing import List, Dict, Any
from sentence_transformers import SentenceTransformer

class KnowledgeBuilder:
    """知识库构建器"""

    def __init__(self, db_manager, indexer, embedding_model="all-MiniLM-L6-v2"):
        self.db = db_manager
        self.indexer = indexer
        self.encoder = SentenceTransformer(embedding_model)

    async def build_knowledge_base(
        self,
        kb_id: str,
        source_type: str,
        source_location: str,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        progress_callback=None
    ) -> Dict[str, Any]:
        """构建知识库"""

        try:
            # 1. 扫描数据源
            documents = await self._scan_source(source_type, source_location)
            if progress_callback:
                progress_callback("扫描完成", 10)

            # 2. 文档分块
            chunks = await self._chunk_documents(documents, chunk_size, chunk_overlap)
            if progress_callback:
                progress_callback(f"分块完成，共{len(chunks)}块", 30)

            # 3. 计算向量
            vectors = await self._compute_embeddings(chunks)
            if progress_callback:
                progress_callback("向量化完成", 60)

            # 4. 保存到数据库
            await self._save_chunks(kb_id, chunks)
            if progress_callback:
                progress_callback("保存完成", 80)

            # 5. 构建索引
            await self._build_index(kb_id, vectors, chunks)
            if progress_callback:
                progress_callback("索引构建完成", 100)

            return {
                "success": True,
                "chunk_count": len(chunks),
                "total_tokens": sum(len(c["content"]) for c in chunks)
            }

        except Exception as e:
            logger.error(f"Knowledge base build failed: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    async def _scan_source(self, source_type: str, location: str) -> List[Dict[str, Any]]:
        """扫描数据源"""
        documents = []

        if source_type == "directory":
            path = Path(location)
            for file_path in path.rglob("*.md"):
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    documents.append({
                        "source": str(file_path),
                        "content": content,
                        "type": "markdown"
                    })

        elif source_type == "web":
            # 网页爬取
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.get(location)
                documents.append({
                    "source": location,
                    "content": response.text,
                    "type": "html"
                })

        return documents

    async def _chunk_documents(
        self,
        documents: List[Dict[str, Any]],
        chunk_size: int,
        chunk_overlap: int
    ) -> List[Dict[str, Any]]:
        """文档分块"""
        chunks = []

        for doc in documents:
            content = doc["content"]

            # 简单分块策略
            for i in range(0, len(content), chunk_size - chunk_overlap):
                chunk_text = content[i:i + chunk_size]

                chunk_id = hashlib.md5(chunk_text.encode()).hexdigest()

                chunks.append({
                    "id": chunk_id,
                    "content": chunk_text,
                    "source": doc["source"],
                    "start_pos": i
                })

        return chunks

    async def _compute_embeddings(self, chunks: List[Dict[str, Any]]) -> np.ndarray:
        """计算向量"""
        texts = [c["content"] for c in chunks]
        vectors = self.encoder.encode(texts, show_progress_bar=True)
        return vectors

    async def _save_chunks(self, kb_id: str, chunks: List[Dict[str, Any]]):
        """保存分块到数据库"""
        with self.db.get_session() as db_session:
            from yfai.store.db import KnowledgeChunk

            for chunk in chunks:
                db_chunk = KnowledgeChunk(
                    id=chunk["id"],
                    knowledge_base_id=kb_id,
                    content=chunk["content"],
                    source_path=chunk["source"],
                    start_position=chunk["start_pos"]
                )
                db_session.add(db_chunk)

            db_session.commit()

    async def _build_index(self, kb_id: str, vectors: np.ndarray, chunks: List[Dict[str, Any]]):
        """构建FAISS索引"""
        metadatas = [{"chunk_id": c["id"], "source": c["source"]} for c in chunks]

        self.indexer.create_index(kb_id)
        self.indexer.add_vectors(kb_id, vectors, metadatas)
        self.indexer.save(kb_id)

# knowledge_page.py 中使用
async def _build_kb(self, kb_id: str):
    """构建知识库"""
    builder = KnowledgeBuilder(self.orchestrator.db_manager, self.indexer)

    # 显示进度对话框
    progress = QProgressDialog("正在构建知识库...", "取消", 0, 100, self)
    progress.setWindowModality(Qt.WindowModality.WindowModal)

    def update_progress(message, value):
        progress.setLabelText(message)
        progress.setValue(value)

    result = await builder.build_knowledge_base(
        kb_id=kb_id,
        source_type="directory",
        source_location="./docs",
        progress_callback=update_progress
    )

    progress.close()

    if result["success"]:
        QMessageBox.information(self, "成功", f"知识库构建完成，共{result['chunk_count']}个分块")
    else:
        QMessageBox.warning(self, "失败", f"构建失败: {result['error']}")
```

**验收标准**:
- [ ] 支持多种数据源（文件/目录/网页）
- [ ] 进度显示
- [ ] 可取消
- [ ] 增量更新
- [ ] 错误恢复

---

### 2.2 逻辑闭环完善

#### ⚠️ 14. 知识库查询集成到聊天
**优先级**: P1 | **估时**: 2-3天 | **难度**: ⭐⭐⭐

**功能描述**:
- 聊天时自动检索知识库
- 将相关上下文注入prompt

**实现方案**:
```python
# orchestrator.py 修改

async def chat(self, user_message: str, session_id: Optional[str] = None, ...):
    # ... 现有代码 ...

    # 获取会话历史
    messages = await self._get_session_messages(session_id)

    # 检查会话是否关联知识库
    kb_id = await self._get_session_kb(session_id)
    if kb_id:
        # 检索相关知识
        relevant_context = await self._retrieve_knowledge(kb_id, user_message)

        if relevant_context:
            # 注入系统提示
            system_message = ChatMessage(
                role="system",
                content=f"参考以下知识库内容回答问题：\n\n{relevant_context}"
            )
            messages.insert(0, system_message)

    # 添加当前消息
    messages.append(ChatMessage(role="user", content=user_message))

    # ... 调用Provider ...

async def _retrieve_knowledge(self, kb_id: str, query: str, top_k: int = 5) -> str:
    """检索知识库"""
    try:
        # 1. 计算查询向量
        query_vector = await self._compute_query_embedding(query)

        # 2. 检索相似文档
        results = self.indexer.search(kb_id, query_vector, top_k=top_k)

        # 3. 格式化上下文
        context_parts = []
        for distance, metadata in results:
            chunk_id = metadata["chunk_id"]

            # 从数据库获取完整内容
            with self.db_manager.get_session() as db_session:
                from yfai.store.db import KnowledgeChunk
                chunk = db_session.query(KnowledgeChunk).filter_by(id=chunk_id).first()

                if chunk:
                    context_parts.append(f"【来源：{chunk.source_path}】\n{chunk.content}")

        return "\n\n---\n\n".join(context_parts)

    except Exception as e:
        logger.error(f"Knowledge retrieval failed: {e}")
        return ""
```

**验收标准**:
- [ ] 自动检索相关知识
- [ ] 相似度阈值可配置
- [ ] 上下文长度控制
- [ ] 显示引用来源
- [ ] 可选启用/禁用

---

#### ⚠️ 15. Agent执行结果反馈优化
**优先级**: P1 | **估时**: 2天 | **难度**: ⭐⭐⭐

**文件**: `yfai/core/agent_runner.py`

**功能描述**:
- 执行步骤的详细反馈
- 失败时的错误诊断
- 重试机制

**实现方案**:
```python
# agent_runner.py

async def _execute_step(
    self,
    step: Dict[str, Any],
    job_run_id: str,
    retry_count: int = 0,
    max_retries: int = 3
) -> Dict[str, Any]:
    """执行单个步骤（带重试）"""

    step_id = str(uuid.uuid4())
    step_type = step.get("type")

    # 创建步骤记录
    job_step = await self._create_job_step(job_run_id, step_id, step)

    try:
        # 执行步骤
        if step_type == "tool_call":
            result = await self.tool_executor(
                step["tool_name"],
                step["params"]
            )
        elif step_type == "llm_call":
            result = await self._execute_llm_step(step)
        else:
            raise ValueError(f"Unknown step type: {step_type}")

        # 更新步骤状态
        await self._update_job_step(step_id, {
            "status": "success",
            "response_snapshot": json.dumps(result, ensure_ascii=False),
            "ended_at": datetime.utcnow()
        })

        return {"success": True, "result": result}

    except Exception as e:
        logger.error(f"Step execution failed: {e}", exc_info=True)

        # 判断是否可重试
        if retry_count < max_retries and self._is_retryable_error(e):
            logger.info(f"Retrying step {step_id} ({retry_count + 1}/{max_retries})")
            await asyncio.sleep(2 ** retry_count)  # 指数退避
            return await self._execute_step(step, job_run_id, retry_count + 1, max_retries)

        # 更新失败状态
        await self._update_job_step(step_id, {
            "status": "failed",
            "error": str(e),
            "ended_at": datetime.utcnow()
        })

        return {
            "success": False,
            "error": str(e),
            "retry_count": retry_count
        }

def _is_retryable_error(self, error: Exception) -> bool:
    """判断错误是否可重试"""
    # 网络错误、超时、临时失败等可重试
    retryable_types = (
        ConnectionError,
        TimeoutError,
        asyncio.TimeoutError
    )

    return isinstance(error, retryable_types)
```

**验收标准**:
- [ ] 步骤失败自动重试
- [ ] 详细错误诊断
- [ ] 执行日志完整
- [ ] UI实时反馈

---

#### ⚠️ 16. 工具审批白名单/黑名单
**优先级**: P1 | **估时**: 2天 | **难度**: ⭐⭐

**文件**: `yfai/security/policy.py`, `yfai/app/main_window.py:337`

**问题描述**:
- TODO标记：保存到白名单/永久允许规则

**实现方案**:
```python
# policy.py

class SecurityPolicy:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.whitelist = set(config.get("security", {}).get("whitelist", []))
        self.blacklist = set(config.get("security", {}).get("blacklist", []))
        self.auto_approve_rules = []  # (pattern, condition)

    def is_whitelisted(self, tool_name: str, params: Dict[str, Any]) -> bool:
        """检查是否在白名单"""
        # 完全匹配
        if tool_name in self.whitelist:
            return True

        # 模式匹配
        for pattern, condition in self.auto_approve_rules:
            if self._match_rule(tool_name, params, pattern, condition):
                return True

        return False

    def is_blacklisted(self, tool_name: str) -> bool:
        """检查是否在黑名单"""
        return tool_name in self.blacklist

    def add_to_whitelist(self, tool_name: str, params: Optional[Dict] = None):
        """添加到白名单"""
        if params:
            # 添加带条件的规则
            self.auto_approve_rules.append((tool_name, params))
        else:
            # 完全白名单
            self.whitelist.add(tool_name)

        self._save_policy()

    def _save_policy(self):
        """持久化策略"""
        policy_file = Path("configs/security_policy.json")
        with open(policy_file, "w") as f:
            json.dump({
                "whitelist": list(self.whitelist),
                "blacklist": list(self.blacklist),
                "auto_approve_rules": self.auto_approve_rules
            }, f, indent=2)

# guard.py 集成
async def request_approval(self, request: ApprovalRequest) -> ApprovalResult:
    # 检查白名单
    if self.security_policy.is_whitelisted(request.tool_name, request.params):
        logger.info(f"Tool {request.tool_name} is whitelisted, auto-approved")
        return ApprovalResult(status=ApprovalStatus.APPROVED, message="Whitelisted")

    # 检查黑名单
    if self.security_policy.is_blacklisted(request.tool_name):
        logger.warning(f"Tool {request.tool_name} is blacklisted, auto-rejected")
        return ApprovalResult(status=ApprovalStatus.REJECTED, message="Blacklisted")

    # ... 正常审批流程 ...

# approval_dialog.py UI
def _on_always_allow_clicked(self):
    """永久允许此类操作"""
    reply = QMessageBox.question(
        self,
        "确认",
        f"确定永久允许 {self.request.tool_name} 操作吗？",
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
    )

    if reply == QMessageBox.StandardButton.Yes:
        self.orchestrator.security_policy.add_to_whitelist(
            self.request.tool_name,
            self.request.params  # 可选：只允许特定参数
        )
        self.accept()
```

**验收标准**:
- [ ] 白名单工具自动通过
- [ ] 黑名单工具自动拒绝
- [ ] UI提供"总是允许"选项
- [ ] 策略持久化
- [ ] 支持模式匹配

---

## 🚀 Phase 3: 功能增强（P2，1-2月）

### 3.1 性能优化

#### 🟡 17. 数据库连接池
**优先级**: P2 | **估时**: 1-2天 | **难度**: ⭐⭐⭐

**实现方案**:
```python
# db.py
from sqlalchemy.pool import QueuePool

class DatabaseManager:
    def __init__(self, db_path: str):
        engine_args = {
            "poolclass": QueuePool,
            "pool_size": 5,
            "max_overflow": 10,
            "pool_timeout": 30,
            "pool_recycle": 3600,
        }

        self.engine = create_engine(
            f"sqlite:///{db_path}",
            echo=False,
            **engine_args
        )
```

---

#### 🟡 18. 向量检索缓存
**优先级**: P2 | **估时**: 1天 | **难度**: ⭐⭐

**实现方案**:
```python
from functools import lru_cache
import hashlib

class VectorIndexer:
    def __init__(self, ...):
        # ... 现有代码 ...
        self.query_cache = {}
        self.cache_ttl = 3600  # 1小时

    def search(self, kb_id: str, query_vector: np.ndarray, top_k: int = 5):
        # 计算查询hash
        query_hash = hashlib.md5(query_vector.tobytes()).hexdigest()
        cache_key = f"{kb_id}:{query_hash}:{top_k}"

        # 检查缓存
        if cache_key in self.query_cache:
            cached_result, timestamp = self.query_cache[cache_key]
            if time.time() - timestamp < self.cache_ttl:
                return cached_result

        # 执行查询
        results = self._do_search(kb_id, query_vector, top_k)

        # 缓存结果
        self.query_cache[cache_key] = (results, time.time())

        return results
```

---

#### 🟡 19. 批量向量计算
**优先级**: P2 | **估时**: 1天 | **难度**: ⭐⭐

**实现方案**:
```python
async def _compute_embeddings_batch(self, chunks: List[Dict], batch_size: int = 32):
    """批量计算向量，提高效率"""
    all_vectors = []

    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]
        texts = [c["content"] for c in batch]

        # 批量编码
        vectors = self.encoder.encode(texts, batch_size=batch_size)
        all_vectors.append(vectors)

    return np.vstack(all_vectors)
```

---

### 3.2 用户体验优化

#### 🟡 20. 聊天历史搜索
**优先级**: P2 | **估时**: 2-3天 | **难度**: ⭐⭐⭐

**实现方案**:
```python
# sessions_page.py 添加搜索框

def _search_sessions(self, keyword: str):
    """搜索会话"""
    with self.orchestrator.db_manager.get_session() as db_session:
        from yfai.store.db import Session, Message

        # 在会话标题和消息内容中搜索
        sessions = db_session.query(Session).join(Message).filter(
            (Session.title.like(f"%{keyword}%")) |
            (Message.content.like(f"%{keyword}%"))
        ).distinct().all()

        self._display_sessions(sessions)
```

---

#### 🟡 21. 导出会话为Markdown
**优先级**: P2 | **估时**: 1天 | **难度**: ⭐⭐

**实现方案**:
```python
def _export_session(self, session_id: str, file_path: str):
    """导出会话为Markdown"""
    with self.orchestrator.db_manager.get_session() as db_session:
        from yfai.store.db import Session, Message

        session = db_session.query(Session).filter_by(id=session_id).first()
        messages = db_session.query(Message).filter_by(session_id=session_id).order_by(Message.created_at).all()

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(f"# {session.title}\n\n")
            f.write(f"创建时间: {session.created_at}\n\n")
            f.write("---\n\n")

            for msg in messages:
                role_icon = "👤" if msg.role == "user" else "🤖"
                f.write(f"## {role_icon} {msg.role.upper()}\n\n")
                f.write(f"{msg.content}\n\n")
                f.write("---\n\n")
```

---

#### 🟡 22. 工具调用预览
**优先级**: P2 | **估时**: 2天 | **难度**: ⭐⭐⭐

**功能描述**:
- 执行工具前显示预览
- 显示将要执行的命令/操作
- 模拟执行结果

**实现方案**:
```python
# approval_dialog.py

def _show_preview(self):
    """显示工具调用预览"""
    preview_text = self._generate_preview(self.request.tool_name, self.request.params)

    preview_dialog = QDialog(self)
    preview_dialog.setWindowTitle("操作预览")

    layout = QVBoxLayout()

    preview_edit = QTextEdit()
    preview_edit.setPlainText(preview_text)
    preview_edit.setReadOnly(True)
    layout.addWidget(preview_edit)

    # ... 按钮 ...

    preview_dialog.exec()

def _generate_preview(self, tool_name: str, params: Dict[str, Any]) -> str:
    """生成预览文本"""
    if tool_name == "shell.exec":
        return f"将执行命令:\n\n{params.get('command')}\n\n工作目录: {params.get('cwd', '当前目录')}"

    elif tool_name == "fs.write":
        return f"将写入文件:\n\n路径: {params.get('path')}\n\n内容预览:\n{params.get('content')[:200]}..."

    # ... 其他工具 ...
```

---

### 3.3 安全性增强

#### 🟡 23. 敏感信息脱敏增强
**优先级**: P2 | **估时**: 1-2天 | **难度**: ⭐⭐

**文件**: `yfai/security/policy.py`

**实现方案**:
```python
import re

class SecurityPolicy:
    # ... 现有代码 ...

    SENSITIVE_PATTERNS = [
        (r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}", "***@***.***"),  # Email
        (r"\b\d{3}-\d{2}-\d{4}\b", "***-**-****"),  # SSN
        (r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b", "**** **** **** ****"),  # Credit Card
        (r"(password|pwd|token|key|secret)\s*[=:]\s*\S+", r"\1=***"),  # Credentials
        (r"(sk-[a-zA-Z0-9]{32,})", "sk-***"),  # API Keys
    ]

    def redact_sensitive_data(self, text: str) -> str:
        """脱敏敏感信息"""
        redacted = text

        for pattern, replacement in self.SENSITIVE_PATTERNS:
            redacted = re.sub(pattern, replacement, redacted, flags=re.IGNORECASE)

        return redacted

    def scan_for_secrets(self, text: str) -> List[str]:
        """扫描潜在的敏感信息"""
        findings = []

        for pattern, _ in self.SENSITIVE_PATTERNS:
            matches = re.findall(pattern, text, flags=re.IGNORECASE)
            if matches:
                findings.extend(matches)

        return findings
```

---

#### 🟡 24. 操作审计报告
**优先级**: P2 | **估时**: 2-3天 | **难度**: ⭐⭐⭐

**功能描述**:
- 生成审计报告
- 按时间/用户/操作类型统计
- 导出PDF/Excel

---

## 📈 Phase 4: 高级功能（P3，2-3月）

### 4.1 多模态支持

#### 🟢 25. 图片输入支持
**优先级**: P3 | **估时**: 3-4天 | **难度**: ⭐⭐⭐⭐

**实现方案**:
```python
# 支持通义千问-VL等多模态模型

class BailianProvider:
    async def chat_with_image(
        self,
        messages: List[ChatMessage],
        images: List[str],  # 图片路径或URL
        model: str = "qwen-vl-plus"
    ):
        # 构造多模态请求
        multimodal_messages = []

        for msg in messages:
            content = [{"text": msg.content}]

            # 添加图片
            if msg.images:
                for img in msg.images:
                    content.append({"image": img})

            multimodal_messages.append({
                "role": msg.role,
                "content": content
            })

        # 调用API
        response = await self.client.call(
            model=model,
            messages=multimodal_messages
        )

        return response
```

---

#### 🟢 26. 语音输入/输出
**优先级**: P3 | **估时**: 4-5天 | **难度**: ⭐⭐⭐⭐

**依赖**:
- 语音识别：Azure Speech / 阿里云ASR
- 语音合成：Azure TTS / 阿里云TTS

---

### 4.2 协作功能

#### 🟢 27. 多用户支持
**优先级**: P3 | **估时**: 5-7天 | **难度**: ⭐⭐⭐⭐⭐

**实现方案**:
```python
# 添加用户系统

class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True)
    username = Column(String(50), unique=True)
    password_hash = Column(String(128))
    role = Column(String(20))  # admin, user, viewer
    created_at = Column(DateTime, default=datetime.utcnow)

# Session关联用户
class Session(Base):
    # ... 现有字段 ...
    user_id = Column(String(36), ForeignKey("users.id"))
    shared_with = Column(Text)  # JSON: [user_ids]
```

---

#### 🟢 28. 会话共享
**优先级**: P3 | **估时**: 2-3天 | **难度**: ⭐⭐⭐

---

### 4.3 插件系统

#### 🟢 29. 自定义工具插件
**优先级**: P3 | **估时**: 5-7天 | **难度**: ⭐⭐⭐⭐⭐

**实现方案**:
```python
# 插件接口
class ToolPlugin(ABC):
    @abstractmethod
    def get_name(self) -> str:
        pass

    @abstractmethod
    def get_description(self) -> str:
        pass

    @abstractmethod
    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        pass

# 插件加载器
class PluginLoader:
    def load_plugins(self, plugin_dir: str):
        """从目录加载插件"""
        for file in Path(plugin_dir).glob("*.py"):
            # 动态导入
            spec = importlib.util.spec_from_file_location(file.stem, file)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # 查找ToolPlugin子类
            for name, obj in inspect.getmembers(module):
                if inspect.isclass(obj) and issubclass(obj, ToolPlugin) and obj != ToolPlugin:
                    plugin = obj()
                    self.register_plugin(plugin)
```

---

## 📋 Phase 5: 测试和文档（持续）

### 5.1 单元测试

#### 🟡 30. 核心模块测试覆盖
**优先级**: P2 | **估时**: 5-7天 | **难度**: ⭐⭐⭐

**实现方案**:
```python
# tests/test_orchestrator.py

import pytest
from yfai.core.orchestrator import Orchestrator

@pytest.fixture
def orchestrator():
    config = load_test_config()
    return Orchestrator(config)

@pytest.mark.asyncio
async def test_create_session(orchestrator):
    session_id = await orchestrator.create_session(title="Test Session")
    assert session_id is not None
    assert len(session_id) == 36  # UUID

@pytest.mark.asyncio
async def test_chat_basic(orchestrator):
    session_id = await orchestrator.create_session()
    response = await orchestrator.chat("Hello", session_id=session_id)
    assert response is not None
    assert response.content != ""

@pytest.mark.asyncio
async def test_stream_chat_error_recovery(orchestrator):
    """测试流式聊天异常恢复"""
    session_id = await orchestrator.create_session()

    # 模拟中断
    chunks = []
    try:
        async for chunk in orchestrator.stream_chat("Test", session_id):
            chunks.append(chunk)
            if len(chunks) == 5:
                raise Exception("Simulated interruption")
    except Exception:
        pass

    # 验证部分内容已保存
    messages = await orchestrator._get_session_messages(session_id)
    assert len(messages) > 0
```

**测试覆盖目标**:
- [ ] orchestrator: 80%+
- [ ] agent_runner: 75%+
- [ ] providers: 70%+
- [ ] security: 90%+
- [ ] localops: 80%+

---

### 5.2 集成测试

#### 🟡 31. 端到端测试
**优先级**: P2 | **估时**: 3-5天 | **难度**: ⭐⭐⭐⭐

**测试场景**:
```python
@pytest.mark.integration
async def test_e2e_agent_execution():
    """端到端测试：创建Agent并执行任务"""

    # 1. 创建Agent
    agent_id = await create_test_agent()

    # 2. 执行任务
    result = await orchestrator.run_agent(
        agent_id=agent_id,
        goal="列出当前目录文件并统计数量"
    )

    # 3. 验证结果
    assert result["status"] == "success"
    assert "步骤" in result["plan"]
    assert result["summary"] != ""

    # 4. 检查数据库记录
    job_runs = get_job_runs(agent_id)
    assert len(job_runs) == 1
    assert job_runs[0]["status"] == "success"
```

---

### 5.3 性能测试

#### 🟡 32. 负载测试
**优先级**: P2 | **估时**: 2-3天 | **难度**: ⭐⭐⭐

**测试指标**:
- 并发聊天支持（目标：10+会话）
- 知识库检索延迟（目标：<500ms）
- 数据库查询性能（目标：<100ms）

---

### 5.4 文档

#### 🟡 33. API文档
**优先级**: P2 | **估时**: 3-4天 | **难度**: ⭐⭐

**使用Sphinx生成**:
```bash
pip install sphinx sphinx-rtd-theme
sphinx-quickstart docs
sphinx-apidoc -o docs/api yfai
make html
```

---

#### 🟡 34. 用户手册
**优先级**: P2 | **估时**: 5-7天 | **难度**: ⭐⭐

**章节**:
1. 快速开始
2. 功能介绍
3. 配置指南
4. 最佳实践
5. 常见问题
6. 故障排查

---

## 🛠 Phase 6: 工程化改进（P2-P3）

### 6.1 代码质量

#### 🟡 35. 类型注解完善
**优先级**: P2 | **估时**: 3-4天 | **难度**: ⭐⭐

**目标**:
- 所有public方法都有类型注解
- mypy检查通过（strict模式）

```python
# 示例
from typing import Optional, List, Dict, Any, AsyncIterator

async def chat(
    self,
    user_message: str,
    session_id: Optional[str] = None,
    provider: Optional[str] = None,
    model: Optional[str] = None,
    stream: bool = False
) -> ChatResponse:
    ...
```

---

#### 🟡 36. 代码风格统一
**优先级**: P2 | **估时**: 1-2天 | **难度**: ⭐

**工具**:
- black（格式化）
- ruff（lint）
- isort（import排序）

**配置**:
```toml
# pyproject.toml
[tool.black]
line-length = 100
target-version = ['py311']

[tool.ruff]
line-length = 100
select = ["E", "F", "I", "N", "UP"]

[tool.isort]
profile = "black"
```

---

### 6.2 CI/CD

#### 🟡 37. GitHub Actions配置
**优先级**: P2 | **估时**: 1-2天 | **难度**: ⭐⭐

**工作流**:
```yaml
# .github/workflows/ci.yml
name: CI

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install poetry
          poetry install

      - name: Lint
        run: poetry run ruff check .

      - name: Type check
        run: poetry run mypy yfai

      - name: Test
        run: poetry run pytest --cov=yfai

      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

---

### 6.3 部署优化

#### 🟢 38. Docker支持
**优先级**: P3 | **估时**: 2-3天 | **难度**: ⭐⭐⭐

**Dockerfile**:
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# 安装依赖
COPY pyproject.toml poetry.lock ./
RUN pip install poetry && poetry install --no-dev

# 复制代码
COPY yfai ./yfai
COPY configs ./configs

# 暴露端口（如果需要Web界面）
EXPOSE 8080

CMD ["poetry", "run", "python", "-m", "yfai.main"]
```

---

#### 🟢 39. 一键安装脚本
**优先级**: P3 | **估时**: 1天 | **难度**: ⭐⭐

**install.sh**:
```bash
#!/bin/bash

echo "YFAI 安装脚本"

# 检查Python版本
python_version=$(python3 --version | cut -d' ' -f2)
required_version="3.11"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo "错误：需要Python 3.11或更高版本"
    exit 1
fi

# 安装Poetry
curl -sSL https://install.python-poetry.org | python3 -

# 安装依赖
poetry install

# 初始化配置
cp configs/config.example.yaml configs/config.yaml
cp configs/.env.example .env

echo "安装完成！"
echo "请编辑 .env 文件配置API密钥"
echo "运行: poetry run python -m yfai.main"
```

---

## 📊 开发优先级总结

### 第1周（必做）
1. ✅ 流式聊天数据丢失修复
2. ✅ 异步回调混乱修复
3. ✅ Provider响应解析修复
4. ✅ UI操作保护

### 第2-3周（紧急）
5. ✅ 数据库事务异常处理
6. ✅ Agent统计原子性
7. ✅ 审计日志实现
8. ✅ MCP WebSocket支持

### 第4-6周（重要）
9. ✅ Cron调度器
10. ✅ 文件/进程触发器
11. ✅ Connector实现
12. ✅ 日志页面
13. ✅ 知识库构建
14. ✅ RAG集成

### 第7-10周（增强）
15. ✅ 知识库查询优化
16. ✅ Agent反馈优化
17. ✅ 审批白名单
18. ✅ 性能优化
19. ✅ UX改进

### 第11-16周（高级）
20. ✅ 多模态支持
21. ✅ 插件系统
22. ✅ 测试覆盖
23. ✅ 文档完善

---

## 🎯 成功指标

### 功能完整性
- [ ] 所有P0问题修复（100%）
- [ ] P1功能实现（≥90%）
- [ ] P2优化完成（≥70%）

### 代码质量
- [ ] 测试覆盖率 ≥75%
- [ ] Mypy类型检查通过
- [ ] Ruff无警告
- [ ] 无已知严重bug

### 性能指标
- [ ] 聊天响应延迟 <2s
- [ ] 知识库检索 <500ms
- [ ] 支持10+并发会话
- [ ] 内存占用 <500MB

### 用户体验
- [ ] UI无崩溃
- [ ] 错误提示友好
- [ ] 操作响应及时
- [ ] 文档完整清晰

---

## 📚 参考资源

### 内部文档
- `CODE_ANALYSIS_REPORT.md` - 完整代码分析
- `CRITICAL_ISSUES_SUMMARY.md` - 关键问题汇总
- `ISSUES_CHECKLIST.csv` - 问题清单
- `ANALYSIS_QUICK_START.md` - 快速指南

### 外部资源
- [PyQt6 文档](https://www.riverbankcomputing.com/static/Docs/PyQt6/)
- [SQLAlchemy 文档](https://docs.sqlalchemy.org/)
- [FAISS 文档](https://github.com/facebookresearch/faiss)
- [阿里云百炼 API](https://help.aliyun.com/zh/model-studio/)

---

## 🤝 贡献指南

### 开发流程
1. Fork项目
2. 创建特性分支（`feature/your-feature`）
3. 提交代码（遵循Conventional Commits）
4. 运行测试（`pytest`）
5. 提交PR

### Commit规范
```
feat: 新功能
fix: Bug修复
docs: 文档更新
style: 代码格式
refactor: 重构
test: 测试
chore: 构建/工具
```

---

## 📞 支持

- **Issue跟踪**: GitHub Issues
- **讨论**: GitHub Discussions
- **邮件**: [your-email]

---

**最后更新**: 2025-11-17
**下次审查**: 每2周更新进度
