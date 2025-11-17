# 关键问题汇总（优先级排序）

## 执行摘要
- **总问题数**: 47 个
- **高严重性**: 20 个
- **中等严重性**: 19 个  
- **低严重性**: 8 个

---

## 🔴 优先级 1：需立即修复（7-10 天内）

### 1. orchestrator.py - 流式聊天数据丢失 ⚠️
**文件**: `/home/user/yfai/yfai/core/orchestrator.py`  
**行号**: 156-220 (stream_chat)  
**问题**: 流式输出过程中如果发生异常，用户已接收的内容不会保存到数据库
```python
# 现有代码 - 存在风险
async for chunk in provider_obj.stream_chat(...):
    full_response += chunk
    yield chunk  # 用户已看到
    # ← 如果此处崩溃，数据库没有记录

# 保存消息 - 全部流式接收后才执行
# 问题：中间可能丢失
```
**影响**: 消息历史不完整，用户看到与数据库记录不一致  
**修复**: 实现保存点或流式缓存机制

---

### 2. agent_runner.py - 异步回调混乱 ⚠️
**文件**: `/home/user/yfai/yfai/security/guard.py`  
**行号**: 163 (request_approval) 和 `/home/user/yfai/yfai/core/agent_runner.py` 389  
**问题**: 同步调用可能是异步的回调函数
```python
# guard.py line 163 - 同步调用
if self.approval_callback:
    result = self.approval_callback(request)  # 如果回调是 async def 会返回 coroutine！

# agent_runner.py line 389 - 期望得到结果
approval_result = await self.security_guard.request_approval(...)
if approval_result.status == ApprovalStatus.REJECTED:  # 如果 result 是 coroutine 会崩溃
```
**影响**: 审批流程完全失效，所有高风险操作可能无法正确处理  
**修复**:
```python
import inspect
if self.approval_callback:
    if inspect.iscoroutinefunction(self.approval_callback):
        result = await self.approval_callback(request)
    else:
        result = self.approval_callback(request)
```

---

### 3. bailian.py & ollama.py - 响应解析崩溃 ⚠️
**文件**: `/home/user/yfai/yfai/providers/bailian.py` 81-91 和 `/home/user/yfai/yfai/providers/ollama.py` 66-79  
**问题**: 无检查地访问 API 响应的数组和对象
```python
# bailian.py line 81 - 数组越界
choice = result["choices"][0]  # 如果 choices 为空会 IndexError

# ollama.py line 66 - None 检查不完整
message = result.get("message", {})  # 但可能返回 None！
return ChatResponse(
    content=message.get("content", ""),  # None.get() 会崩溃
)
```
**影响**: LLM 返回异常格式时应用直接崩溃  
**修复**:
```python
# 验证结构
if not result.get("choices") or len(result["choices"]) == 0:
    raise ValueError("Empty choices in response")
choice = result["choices"][0]

# 检查 None
message = result.get("message") or {}
content = message.get("content", "") if message else ""
```

---

### 4. chat_widget.py - UI 操作无保护 ⚠️
**文件**: `/home/user/yfai/yfai/app/widgets/chat_widget.py`  
**行号**: 185 和 168-196  
**问题**: 直接调用 findChild() 的返回值，可能为 None
```python
# line 185 - 无保护地访问
assistant_bubble.findChild(QLabel).setText(full_response)
# findChild() 可能返回 None，导致 AttributeError

# line 168-196 - 整个流式循环无保护
async for chunk in self.orchestrator.stream_chat(...):
    full_response += chunk
    assistant_bubble.findChild(QLabel).setText(full_response)  # 任何地方失败都会崩溃
```
**影响**: 聊天功能经常崩溃，用户体验差  
**修复**:
```python
label = assistant_bubble.findChild(QLabel)
if label:
    label.setText(full_response)
else:
    logger.error("QLabel not found in message bubble")
```

---

### 5. 所有异步任务 - 异常处理缺失 ⚠️
**文件**: 多个文件  
**行号**: 
- `/home/user/yfai/yfai/app/widgets/chat_widget.py` 150, 196
- `/home/user/yfai/yfai/automation/scheduler.py` 54, 90, 96
- `/home/user/yfai/yfai/app/main_window.py` 315

**问题**: create_task() 创建的任务异常会被吞没
```python
# 当前代码 - 异常无人处理
asyncio.create_task(self._main_loop())
asyncio.create_task(create())

# 如果任务异常，没人知道
```
**影响**: 后台任务失败且无通知，应用状态不一致  
**修复**:
```python
async def safe_async_task():
    try:
        # 执行任务
        pass
    except Exception as e:
        logger.error(f"Async task failed: {e}")

task = asyncio.create_task(safe_async_task())
# 或者添加完成回调
def handle_exception(t):
    if t.exception():
        logger.error(f"Task failed: {t.exception()}")
task.add_done_callback(handle_exception)
```

---

### 6. bailian.py - 流式响应数组越界 ⚠️
**文件**: `/home/user/yfai/yfai/providers/bailian.py`  
**行号**: 146-150  
**问题**: 流式响应中也存在数组越界问题
```python
if "choices" in chunk and len(chunk["choices"]) > 0:
    delta = chunk["choices"][0].get("delta", {})  # 这里也需要 None 检查
    content = delta.get("content", "")
```

---

### 7. guard.py - 审计日志未实现 ⚠️
**文件**: `/home/user/yfai/yfai/security/guard.py`  
**行号**: 188  
**问题**: 审计日志只打印不持久化
```python
def _audit_log(self, request: ApprovalRequest, result: ApprovalResult) -> None:
    # TODO: 写入数据库  ← 还是 TODO！
    log_entry = {...}
    print(f"[AUDIT] {log_entry}")  # 只打印到控制台
```
**影响**: 无法追踪安全决策历史，合规性问题  
**修复**: 实现数据库审计日志表

---

## 🟡 优先级 2：应尽快修复（2-4 周内）

### 8. orchestrator.py - 数据库事务异常处理
**文件**: `/home/user/yfai/yfai/core/orchestrator.py`  
**行号**: 75-83, 115-123, 181-189, 209-219, 268-280, 299-309, 321-333  
**问题**: commit() 失败时无异常处理
```python
with self.db_manager.get_session() as db_session:
    db_session.add(session)
    db_session.commit()  # ← 如果失败，无异常捕捉
    # 会话 ID 已设置但数据库可能未提交
```
**修复**: 统一的异常处理模式
```python
try:
    with self.db_manager.get_session() as db_session:
        db_session.add(session)
        db_session.commit()
except Exception as e:
    logger.error(f"Failed to save session: {e}")
    raise
```

---

### 9. orchestrator.py - JSON 参数序列化
**文件**: `/home/user/yfai/yfai/core/orchestrator.py`  
**行号**: 274  
**问题**: 使用 str() 而非 JSON 序列化
```python
# 错误的方式
params=str(params),  # 产生类似 "{'key': 'value'}" 的字符串

# 正确的方式
params=json.dumps(params, ensure_ascii=False),
```

---

### 10. agent_runner.py - 状态更新不完整
**文件**: `/home/user/yfai/yfai/core/agent_runner.py`  
**行号**: 286-339  
**问题**: 异常时 JobRun status 不更新
```python
try:
    # 执行步骤...
except Exception as e:
    # 只更新 error 字段
    await self._update_job_run(job_run["id"], {
        "status": "failed",  # ← 这里应该设置 status 为 "failed"
        "error": str(e),
        "ended_at": datetime.utcnow(),
    })
```

---

### 11. agent_runner.py - 原子性问题
**文件**: `/home/user/yfai/yfai/core/agent_runner.py`  
**行号**: 70-81  
**问题**: agent 统计信息更新不是原子操作
```python
# 现有 - 非原子
agent = db_session.query(Agent).filter_by(id=agent_id).first()
agent.usage_count += 1  # 读取-修改-写入
agent.last_used_at = datetime.utcnow()
db_session.commit()

# 应该使用原子操作
db_session.query(Agent).filter_by(id=agent_id).update({
    Agent.usage_count: Agent.usage_count + 1,
    Agent.last_used_at: datetime.utcnow(),
})
```

---

### 12. agent_runner.py - 计划生成的错误隐藏
**文件**: `/home/user/yfai/yfai/core/agent_runner.py`  
**行号**: 220-248  
**问题**: JSON 解析失败后回退到简单计划，原始错误丢失
```python
try:
    plan = json.loads(content)
except json.JSONDecodeError:
    # 记录原始响应用于调试
    logger.warning(f"Failed to parse plan JSON. Raw response:\n{content}")
    return {
        "goal": goal,
        "steps": [{"index": 0, "type": "analysis", ...}]
    }
```

---

### 13. orchestrator.py - response 为 None 检查
**文件**: `/home/user/yfai/yfai/core/orchestrator.py`  
**行号**: 132-137, 139-154  
**问题**: manager.chat() 可能返回 None
```python
# 现有代码
response = await self.provider_manager.chat(...)
if response:  # ChatResponse 对象总是 truthy
    assistant_msg_id = ...
    message = Message(..., content=response.content)  # 如果 response 是 None 会崩溃

# 应该检查
if response is not None:
    # ...
```

---

## 🟢 优先级 3：优化项（1-2 个月）

### 14. guard.py - 脱敏逻辑改进
**文件**: `/home/user/yfai/yfai/security/guard.py`  
**行号**: 213-223  
**问题**: 简单的字符串替换，改用正则表达式

### 15. ollama.py - 模型拉取进度报告
**文件**: `/home/user/yfai/yfai/providers/ollama.py`  
**行号**: 152-172  
**问题**: 600 秒超时无进度报告

---

## 快速修复清单

### 第 1 天（必做）
- [ ] agent_runner.py 389 行 - 修复异步回调问题
- [ ] bailian.py 81 行 - 添加 choices 数组长度检查  
- [ ] ollama.py 66 行 - 添加 message None 检查
- [ ] chat_widget.py 185 行 - 检查 findChild 返回值

### 第 2-3 天（紧急）
- [ ] 所有 create_task() - 添加异常处理
- [ ] orchestrator.py stream_chat - 实现保存点
- [ ] guard.py request_approval - 修复同步/异步混乱

### 第 4-7 天（重要）
- [ ] 数据库事务 - 统一异常处理
- [ ] JSON 参数 - 改用 json.dumps()
- [ ] agent 统计 - 使用原子操作
- [ ] 审计日志 - 实现数据库持久化

---

## 测试建议

### 单元测试应覆盖
1. stream_chat 中断场景
2. Provider 返回 None 或异常格式
3. 异步任务异常处理
4. 数据库连接失败

### 集成测试应覆盖
1. 流式聊天中网络中断
2. LLM 返回空或格式错误
3. 审批流程中的回调异常
4. 并发 Agent 执行

---

## 文件位置速查表

| 问题 | 文件 | 行号 |
|------|------|------|
| 流式聊天数据丢失 | orchestrator.py | 156-220 |
| 异步回调混乱 | guard.py, agent_runner.py | 163, 389 |
| 响应解析崩溃 | bailian.py, ollama.py | 81-91, 66-79 |
| UI 操作无保护 | chat_widget.py | 168-196, 185 |
| 异步任务异常 | chat_widget.py, scheduler.py | 150, 54 |
| 数据库事务 | orchestrator.py 等 | 多处 |
| JSON 序列化 | orchestrator.py | 274 |
| 审计日志 | guard.py | 188 |

