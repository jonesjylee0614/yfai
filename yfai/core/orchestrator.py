"""核心调度器

负责对话编排、工具路由、计划执行等核心逻辑
"""

import uuid
from datetime import datetime
from typing import Any, AsyncIterator, Dict, List, Optional

from ..providers import ChatMessage, ChatResponse, ProviderManager
from ..mcp import McpClient, McpRegistry
from ..localops import FileSystemOps, ShellOps, ProcessOps, NetworkOps
from ..security import SecurityGuard, SecurityPolicy, ApprovalRequest, ApprovalResult, RiskLevel
from ..store import Assistant, DatabaseManager, Message, Session, ToolCall, ProviderStatus
from .agent_runner import AgentRunner


class Orchestrator:
    """核心调度器"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config

        # 初始化各模块
        self.provider_manager = ProviderManager(config)
        self.mcp_registry = McpRegistry()
        self.security_guard = SecurityGuard(config)
        self.security_policy = SecurityPolicy(config)

        # 初始化数据库
        db_path = config.get("database", {}).get("path", "data/yfai.db")
        self.db_manager = DatabaseManager(db_path)

        # 初始化本地操作
        whitelist = config.get("local_ops", {}).get("roots_whitelist", [])
        self.fs_ops = FileSystemOps(whitelist)
        self.shell_ops = ShellOps(
            default_shell=config.get("local_ops", {}).get("shell", {}).get("default", "powershell"),
            timeout=config.get("local_ops", {}).get("shell", {}).get("timeout", 300),
            wsl_enabled=config.get("local_ops", {}).get("shell", {}).get("wsl", False),
        )
        self.process_ops = ProcessOps()
        self.network_ops = NetworkOps()

        # 初始化 AgentRunner
        self.agent_runner = AgentRunner(
            db_manager=self.db_manager,
            provider_manager=self.provider_manager,
            security_guard=self.security_guard,
            security_policy=self.security_policy,
            tool_executor=self._execute_tool_internal,
        )

        # 当前会话
        self.current_session_id: Optional[str] = None

    def update_config(self, new_config: Dict[str, Any]) -> None:
        """刷新运行时配置并重新初始化依赖"""

        self.config = new_config
        self.provider_manager = ProviderManager(new_config)
        self.security_guard.apply_config(new_config)
        self.security_policy = SecurityPolicy(new_config)
        self.agent_runner.provider_manager = self.provider_manager
        self.agent_runner.security_guard = self.security_guard
        self.agent_runner.security_policy = self.security_policy

    async def create_session(
        self,
        title: str = "新对话",
        assistant_id: Optional[str] = None,
        knowledge_base_id: Optional[str] = None,
    ) -> str:
        """创建会话

        Args:
            title: 会话标题
            assistant_id: 助手ID
            knowledge_base_id: 知识库ID

        Returns:
            str: 会话ID
        """
        session_id = str(uuid.uuid4())

        with self.db_manager.get_session() as db_session:
            session = Session(
                id=session_id,
                title=title,
                assistant_id=assistant_id,
                knowledge_base_id=knowledge_base_id,
            )
            db_session.add(session)
            db_session.commit()

            if assistant_id:
                assistant = (
                    db_session.query(Assistant).filter(Assistant.id == assistant_id).first()
                )
                if assistant:
                    assistant.usage_count = (assistant.usage_count or 0) + 1
                    assistant.last_used_at = datetime.utcnow()
                    if assistant.system_prompt:
                        system_message = Message(
                            id=str(uuid.uuid4()),
                            session_id=session_id,
                            role="system",
                            content=assistant.system_prompt,
                            provider=assistant.provider,
                            model=assistant.model,
                        )
                        db_session.add(system_message)
                db_session.commit()

        self.current_session_id = session_id
        return session_id

    async def chat(
        self,
        user_message: str,
        session_id: Optional[str] = None,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        stream: bool = False,
    ) -> ChatResponse:
        """发送聊天消息

        Args:
            user_message: 用户消息
            session_id: 会话ID
            provider: Provider名称
            model: 模型名称
            stream: 是否流式输出

        Returns:
            ChatResponse: 响应
        """
        session_id = session_id or self.current_session_id

        if not session_id:
            session_id = await self.create_session()

        requested_provider = provider or self.provider_manager.get_default_provider_name()
        requested_model = model or self.provider_manager.get_default_model(requested_provider)

        # 保存用户消息
        user_msg_id = str(uuid.uuid4())
        with self.db_manager.get_session() as db_session:
            message = Message(
                id=user_msg_id,
                session_id=session_id,
                role="user",
                content=user_message,
                provider=requested_provider,
                model=requested_model,
            )
            db_session.add(message)
            db_session.commit()

        # 获取会话历史
        messages = await self._get_session_messages(session_id)

        # 添加当前消息
        messages.append(ChatMessage(role="user", content=user_message))

        # 调用Provider
        response = await self.provider_manager.chat(
            messages=messages,
            provider_name=provider,
            model=model,
            stream=stream,
        )

        if response:
            provider_used = response.provider or requested_provider
            model_used = response.model or requested_model

            # 更新 Provider 使用统计
            await self._update_provider_usage(
                provider_name=provider_used,
                model_name=model_used,
                success=True,
            )

            # 保存助手消息
            assistant_msg_id = str(uuid.uuid4())
            with self.db_manager.get_session() as db_session:
                message = Message(
                    id=assistant_msg_id,
                    session_id=session_id,
                    role="assistant",
                    content=response.content,
                    provider=provider_used,
                    model=model_used,
                )
                db_session.add(message)
                db_session.commit()
        else:
            # 记录失败
            await self._update_provider_usage(
                provider_name=requested_provider,
                model_name=requested_model,
                success=False,
                error="Provider 返回空响应",
            )

        return response

    async def stream_chat(
        self,
        user_message: str,
        session_id: Optional[str] = None,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        context: Optional[str] = None,
    ) -> AsyncIterator[str]:
        """流式聊天

        Args:
            user_message: 用户消息
            session_id: 会话ID
            provider: Provider名称
            model: 模型名称
            context: 附加的系统/检索上下文

        Yields:
            str: 流式输出的文本片段
        """
        session_id = session_id or self.current_session_id

        if not session_id:
            session_id = await self.create_session()

        requested_provider = provider or self.provider_manager.get_default_provider_name()
        requested_model = model or self.provider_manager.get_default_model(requested_provider)

        # 保存用户消息
        user_msg_id = str(uuid.uuid4())
        with self.db_manager.get_session() as db_session:
            message = Message(
                id=user_msg_id,
                session_id=session_id,
                role="user",
                content=user_message,
                provider=requested_provider,
                model=requested_model,
            )
            db_session.add(message)
            db_session.commit()

        # 获取会话历史
        messages = await self._get_session_messages(session_id)
        if context:
            messages.append(ChatMessage(role="system", content=context))
        messages.append(ChatMessage(role="user", content=user_message))

        # 获取Provider
        provider_obj = self.provider_manager.get_provider(provider)
        provider_used = provider or self.provider_manager.get_default_provider_name()
        if not provider_obj:
            yield "错误: Provider不可用"
            return

        # 流式输出
        full_response = ""
        async for chunk in provider_obj.stream_chat(messages, model=model):
            full_response += chunk
            yield chunk

        # 保存完整响应
        assistant_msg_id = str(uuid.uuid4())
        resolved_model = model or provider_obj.default_model
        with self.db_manager.get_session() as db_session:
            message = Message(
                id=assistant_msg_id,
                session_id=session_id,
                role="assistant",
                content=full_response,
                provider=provider_used,
                model=resolved_model,
            )
            db_session.add(message)
            db_session.commit()

        # 更新 Provider 使用统计
        await self._update_provider_usage(
            provider_name=provider_used,
            model_name=resolved_model,
            success=True,
        )

    async def _get_session_messages(self, session_id: str) -> List[ChatMessage]:
        """获取会话消息历史

        Args:
            session_id: 会话ID

        Returns:
            List[ChatMessage]: 消息列表
        """
        with self.db_manager.get_session() as db_session:
            messages = (
                db_session.query(Message)
                .filter(Message.session_id == session_id)
                .order_by(Message.created_at)
                .all()
            )

            return [
                ChatMessage(role=msg.role, content=msg.content) for msg in messages
            ]

    async def execute_tool(
        self,
        tool_name: str,
        params: Dict[str, Any],
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """执行工具

        Args:
            tool_name: 工具名称
            params: 参数
            session_id: 会话ID

        Returns:
            Dict[str, Any]: 执行结果
        """
        session_id = session_id or self.current_session_id

        # 记录工具调用
        tool_call_id = str(uuid.uuid4())

        # 判断工具类型和风险等级
        tool_type = self._get_tool_type(tool_name)
        risk_level = self._get_risk_level(tool_name, params)

        # 创建工具调用记录
        with self.db_manager.get_session() as db_session:
            tool_call = ToolCall(
                id=tool_call_id,
                session_id=session_id,
                tool_name=tool_name,
                tool_type=tool_type,
                params=str(params),
                risk_level=risk_level,
                status="pending",
                started_at=datetime.utcnow(),
            )
            db_session.add(tool_call)
            db_session.commit()

        # 检查是否需要审批
        if self.security_guard._needs_approval(RiskLevel(risk_level)):
            # 请求审批
            approval_request = ApprovalRequest(
                tool_name=tool_name,
                tool_type=tool_type,
                params=params,
                risk_level=RiskLevel(risk_level),
                description=f"执行工具: {tool_name}",
            )

            approval_result = await self.security_guard.request_approval(
                approval_request
            )

            if approval_result.status != "approved":
                # 更新工具调用记录
                with self.db_manager.get_session() as db_session:
                    tool_call = (
                        db_session.query(ToolCall)
                        .filter(ToolCall.id == tool_call_id)
                        .first()
                    )
                    if tool_call:
                        tool_call.status = "rejected"
                        tool_call.approved_by = approval_result.approved_by
                        tool_call.ended_at = datetime.utcnow()
                        db_session.commit()

                return {
                    "success": False,
                    "error": "操作被拒绝",
                    "reason": approval_result.reason,
                }

        # 执行工具
        result = await self._execute_tool_internal(tool_name, params)

        # 更新工具调用记录
        with self.db_manager.get_session() as db_session:
            tool_call = (
                db_session.query(ToolCall).filter(ToolCall.id == tool_call_id).first()
            )
            if tool_call:
                tool_call.status = "success" if result.get("success") else "failed"
                tool_call.stdout = str(result.get("stdout", ""))
                tool_call.stderr = str(result.get("stderr", ""))
                tool_call.error = result.get("error")
                tool_call.exit_code = result.get("exit_code", 0)
                tool_call.ended_at = datetime.utcnow()
                tool_call.approved_by = "user"
                db_session.commit()

        return result

    async def get_last_assistant_metadata(self, session_id: Optional[str]) -> Optional[Dict[str, Optional[str]]]:
        """获取指定会话最近一次助手消息的 Provider/模型信息"""
        if not session_id:
            return None
        with self.db_manager.get_session() as db_session:
            message = (
                db_session.query(Message)
                .filter(Message.session_id == session_id, Message.role == "assistant")
                .order_by(Message.created_at.desc())
                .first()
            )
            if not message:
                return None
            return {"provider": message.provider, "model": message.model}

    def _get_tool_type(self, tool_name: str) -> str:
        """获取工具类型

        Args:
            tool_name: 工具名称

        Returns:
            str: 工具类型
        """
        if tool_name.startswith("fs."):
            return "local"
        elif tool_name.startswith("shell."):
            return "local"
        elif tool_name.startswith("process."):
            return "local"
        elif tool_name.startswith("net."):
            return "local"
        else:
            return "mcp"

    def _get_risk_level(self, tool_name: str, params: Dict[str, Any]) -> str:
        """获取风险等级

        Args:
            tool_name: 工具名称
            params: 参数

        Returns:
            str: 风险等级
        """
        # 根据工具名称判断
        if "delete" in tool_name or "kill" in tool_name:
            return "high"
        elif "write" in tool_name or "exec" in tool_name:
            return "medium"
        elif "read" in tool_name or "list" in tool_name:
            return "low"
        else:
            return "medium"

    async def _execute_tool_internal(
        self, tool_name: str, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """内部执行工具

        Args:
            tool_name: 工具名称
            params: 参数

        Returns:
            Dict[str, Any]: 执行结果
        """
        # 文件系统操作
        if tool_name == "fs.read":
            return self.fs_ops.read(**params)
        elif tool_name == "fs.write":
            return self.fs_ops.write(**params)
        elif tool_name == "fs.list":
            return self.fs_ops.list_dir(**params)
        elif tool_name == "fs.delete":
            return self.fs_ops.delete(**params)
        elif tool_name == "fs.search":
            return self.fs_ops.search(**params)

        # Shell操作
        elif tool_name == "shell.exec":
            return await self.shell_ops.execute(**params)

        # 进程操作
        elif tool_name == "process.list":
            return self.process_ops.list_processes(**params)
        elif tool_name == "process.get":
            return self.process_ops.get_process(**params)
        elif tool_name == "process.kill":
            return self.process_ops.kill_process(**params)
        elif tool_name == "process.system_info":
            return self.process_ops.get_system_info()

        # 网络操作
        elif tool_name == "net.http":
            result = await self.network_ops.http_request(**params)
            # 持久化网络内容到审计日志
            if result.get("success") and result.get("body"):
                await self._persist_web_content(params.get("url", ""), result.get("body", ""), params)
            return result
        elif tool_name == "net.check_port":
            return self.network_ops.check_port(**params)
        elif tool_name == "net.local_ip":
            return self.network_ops.get_local_ip()
        elif tool_name == "net.search":
            # 网络搜索（假设后续会添加）
            result = await self._web_search(**params)
            # 持久化搜索结果
            if result.get("success") and result.get("results"):
                await self._persist_search_results(params.get("query", ""), result.get("results", []))
            return result

        else:
            return {"success": False, "error": f"未知工具: {tool_name}"}

    async def run_agent(
        self,
        agent_id: str,
        goal: str,
        session_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """运行智能体

        Args:
            agent_id: 智能体ID
            goal: 用户目标描述
            session_id: 会话ID(可选)
            context: 额外上下文(可选)

        Returns:
            执行结果字典
        """
        session_id = session_id or self.current_session_id

        if not session_id:
            session_id = await self.create_session(title=f"Agent: {goal[:50]}")

        return await self.agent_runner.run_agent(
            agent_id=agent_id,
            goal=goal,
            session_id=session_id,
            context=context,
        )

    async def health_check(self) -> Dict[str, Any]:
        """健康检查

        Returns:
            Dict[str, Any]: 健康状态
        """
        provider_health = await self.provider_manager.check_health_all()

        # 将健康状态写入数据库
        await self._update_provider_health_status(provider_health)

        return {
            "providers": provider_health,
            "database": self.db_manager is not None,
            "mcp_servers": self.mcp_registry.get_stats(),
        }

    async def _update_provider_health_status(self, health_status: Dict[str, bool]) -> None:
        """更新 Provider 健康状态到数据库

        Args:
            health_status: Provider 健康状态字典
        """
        try:
            with self.db_manager.get_session() as db_session:
                for provider_name, is_healthy in health_status.items():
                    status = db_session.query(ProviderStatus).filter_by(
                        provider_name=provider_name
                    ).first()

                    if status:
                        status.is_healthy = is_healthy
                        status.last_check_at = datetime.utcnow()
                        if not is_healthy:
                            status.error_message = "健康检查失败"
                        else:
                            status.error_message = None
                    else:
                        status = ProviderStatus(
                            provider_name=provider_name,
                            is_healthy=is_healthy,
                            last_check_at=datetime.utcnow(),
                            error_message="健康检查失败" if not is_healthy else None,
                        )
                        db_session.add(status)

                db_session.commit()
        except Exception as e:
            print(f"更新 Provider 健康状态失败: {e}")

    async def _update_provider_usage(
        self,
        provider_name: str,
        model_name: Optional[str] = None,
        success: bool = True,
        error: Optional[str] = None,
    ) -> None:
        """更新 Provider 使用统计

        Args:
            provider_name: Provider 名称
            model_name: 模型名称
            success: 是否成功
            error: 错误信息
        """
        try:
            with self.db_manager.get_session() as db_session:
                status = db_session.query(ProviderStatus).filter_by(
                    provider_name=provider_name
                ).first()

                if status:
                    status.total_requests += 1
                    if not success:
                        status.failed_requests += 1
                        status.error_message = error
                    status.last_used_at = datetime.utcnow()
                    if model_name:
                        status.current_model = model_name
                else:
                    status = ProviderStatus(
                        provider_name=provider_name,
                        total_requests=1,
                        failed_requests=0 if success else 1,
                        last_used_at=datetime.utcnow(),
                        current_model=model_name,
                        error_message=error if not success else None,
                    )
                    db_session.add(status)

                db_session.commit()
        except Exception as e:
            print(f"更新 Provider 使用统计失败: {e}")

    async def _persist_web_content(
        self,
        url: str,
        content: str,
        params: Dict[str, Any],
    ) -> None:
        """持久化网络内容到审计日志

        Args:
            url: 网址
            content: 网页内容
            params: 请求参数
        """
        try:
            import json
            with self.db_manager.get_session() as db_session:
                log = AuditLog(
                    id=str(uuid.uuid4()),
                    timestamp=datetime.utcnow(),
                    action_type="web_fetch",
                    tool_name="net.http",
                    risk_level="low",
                    request_data=json.dumps({
                        "url": url,
                        "method": params.get("method", "GET"),
                        "headers": params.get("headers"),
                    }, ensure_ascii=False),
                    result_data=json.dumps({
                        "url": url,
                        "content_length": len(content),
                        "content_preview": content[:500] if len(content) > 500 else content,
                    }, ensure_ascii=False),
                    session_id=self.current_session_id,
                )
                db_session.add(log)
                db_session.commit()
        except Exception as e:
            print(f"持久化网络内容失败: {e}")

    async def _persist_search_results(
        self,
        query: str,
        results: List[Dict[str, Any]],
    ) -> None:
        """持久化搜索结果到审计日志

        Args:
            query: 搜索查询
            results: 搜索结果列表
        """
        try:
            import json
            with self.db_manager.get_session() as db_session:
                log = AuditLog(
                    id=str(uuid.uuid4()),
                    timestamp=datetime.utcnow(),
                    action_type="web_search",
                    tool_name="net.search",
                    risk_level="low",
                    request_data=json.dumps({
                        "query": query,
                    }, ensure_ascii=False),
                    result_data=json.dumps({
                        "query": query,
                        "result_count": len(results),
                        "results": results[:5],  # 只保存前5个结果
                    }, ensure_ascii=False),
                    session_id=self.current_session_id,
                )
                db_session.add(log)
                db_session.commit()
        except Exception as e:
            print(f"持久化搜索结果失败: {e}")

    async def _web_search(self, query: str, count: int = 5) -> Dict[str, Any]:
        """执行网络搜索（占位实现）

        Args:
            query: 搜索查询
            count: 返回结果数量

        Returns:
            搜索结果
        """
        # TODO: 实现实际的搜索功能（集成搜索 API）
        return {
            "success": True,
            "query": query,
            "results": [],
            "message": "搜索功能待实现，请配置搜索 API",
        }

