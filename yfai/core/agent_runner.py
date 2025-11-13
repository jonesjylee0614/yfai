"""智能体运行器模块

负责智能体的计划生成、步骤执行和任务管理
"""

import asyncio
import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Callable

from yfai.providers.manager import ProviderManager
from yfai.security.guard import SecurityGuard
from yfai.store.db import DatabaseManager, Agent, JobRun, JobStep


class AgentRunner:
    """智能体运行器

    负责:
    1. 根据用户目标生成执行计划
    2. 顺序执行步骤(调用工具/模型/Connector)
    3. 记录每步的执行结果
    4. 与安全守卫集成,进行权限检查
    """

    def __init__(
        self,
        db_manager: DatabaseManager,
        provider_manager: ProviderManager,
        security_guard: SecurityGuard,
        tool_executor: Optional[Callable] = None,
    ):
        """初始化 AgentRunner

        Args:
            db_manager: 数据库管理器
            provider_manager: Provider 管理器
            security_guard: 安全守卫
            tool_executor: 工具执行器(可选)
        """
        self.db = db_manager
        self.provider_manager = provider_manager
        self.security_guard = security_guard
        self.tool_executor = tool_executor

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
        # 1. 加载智能体配置
        with self.db.get_session() as db_session:
            agent = db_session.query(Agent).filter_by(id=agent_id).first()
            if not agent:
                raise ValueError(f"Agent not found: {agent_id}")

            if not agent.is_enabled:
                raise ValueError(f"Agent is disabled: {agent.name}")

            # 更新使用统计
            agent.usage_count += 1
            agent.last_used_at = datetime.utcnow()
            db_session.commit()

            agent_dict = agent.to_dict()

        # 2. 创建 JobRun 记录
        job_run = await self._create_job_run(
            agent_id=agent_id,
            goal=goal,
            session_id=session_id,
        )

        try:
            # 3. 生成执行计划
            plan = await self._generate_plan(agent_dict, goal, context)

            # 更新 JobRun 的计划
            await self._update_job_run(job_run["id"], {
                "plan": json.dumps(plan, ensure_ascii=False),
                "status": "running",
                "started_at": datetime.utcnow(),
            })

            # 4. 执行计划步骤
            results = []
            for idx, step in enumerate(plan["steps"]):
                step_result = await self._execute_step(
                    job_run["id"],
                    idx,
                    step,
                    agent_dict,
                )
                results.append(step_result)

                # 检查停止条件
                if step_result["status"] == "failed" and not step.get("continue_on_error"):
                    break

                # 检查是否达到最大步骤数
                if idx + 1 >= agent_dict["max_steps"]:
                    break

            # 5. 生成总结
            summary = await self._generate_summary(agent_dict, goal, plan, results)

            # 6. 更新 JobRun 状态
            final_status = "success" if all(r["status"] == "success" for r in results) else "failed"
            await self._update_job_run(job_run["id"], {
                "status": final_status,
                "summary": summary,
                "ended_at": datetime.utcnow(),
            })

            return {
                "job_id": job_run["id"],
                "status": final_status,
                "plan": plan,
                "results": results,
                "summary": summary,
            }

        except Exception as e:
            # 更新失败状态
            await self._update_job_run(job_run["id"], {
                "status": "failed",
                "error": str(e),
                "ended_at": datetime.utcnow(),
            })
            raise

    async def _generate_plan(
        self,
        agent: Dict[str, Any],
        goal: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """生成执行计划

        Args:
            agent: 智能体配置
            goal: 用户目标
            context: 额外上下文

        Returns:
            计划字典
        """
        # 构建规划提示词
        planning_prompt = f"""
你是一个智能任务规划助手。根据以下信息生成详细的执行计划:

**智能体信息:**
- 名称: {agent['name']}
- 描述: {agent['description']}
- 可用工具: {', '.join(agent['allowed_tools'])}

**用户目标:**
{goal}

**要求:**
1. 将目标分解为具体的、可执行的步骤
2. 每个步骤应该明确指定需要调用的工具或执行的操作
3. 步骤之间应该有逻辑关联
4. 考虑错误处理和异常情况
5. 生成JSON格式的计划

**JSON格式:**
{{
    "goal": "用户目标描述",
    "steps": [
        {{
            "index": 0,
            "type": "tool|model|analysis",
            "name": "步骤名称",
            "description": "步骤描述",
            "tool": "工具名称(如果type是tool)",
            "params": {{"参数": "值"}},
            "expected_output": "预期输出",
            "continue_on_error": false
        }}
    ]
}}
"""

        # 调用 LLM 生成计划
        provider = agent.get("default_provider") or "bailian"
        model = agent.get("default_model") or "qwen-plus"

        messages = [
            {"role": "system", "content": agent["system_prompt"]},
            {"role": "user", "content": planning_prompt},
        ]

        response = await self.provider_manager.chat(
            provider=provider,
            model=model,
            messages=messages,
            temperature=0.3,
        )

        # 解析计划
        try:
            # 尝试从响应中提取 JSON
            content = response.get("content", "")
            # 查找 JSON 代码块
            if "```json" in content:
                json_start = content.find("```json") + 7
                json_end = content.find("```", json_start)
                content = content[json_start:json_end].strip()
            elif "```" in content:
                json_start = content.find("```") + 3
                json_end = content.find("```", json_start)
                content = content[json_start:json_end].strip()

            plan = json.loads(content)
            return plan
        except json.JSONDecodeError:
            # 如果解析失败,返回简单计划
            return {
                "goal": goal,
                "steps": [
                    {
                        "index": 0,
                        "type": "analysis",
                        "name": "分析目标",
                        "description": goal,
                        "continue_on_error": False,
                    }
                ],
            }

    async def _execute_step(
        self,
        job_id: str,
        step_index: int,
        step: Dict[str, Any],
        agent: Dict[str, Any],
    ) -> Dict[str, Any]:
        """执行单个步骤

        Args:
            job_id: JobRun ID
            step_index: 步骤索引
            step: 步骤配置
            agent: 智能体配置

        Returns:
            步骤执行结果
        """
        step_id = str(uuid.uuid4())
        started_at = datetime.utcnow()

        # 创建 JobStep 记录
        with self.db.get_session() as db_session:
            job_step = JobStep(
                id=step_id,
                job_id=job_id,
                step_index=step_index,
                step_type=step.get("type", "unknown"),
                step_name=step.get("name", f"Step {step_index}"),
                request_snapshot=json.dumps(step, ensure_ascii=False),
                status="running",
                started_at=started_at,
            )
            db_session.add(job_step)
            db_session.commit()

        try:
            # 执行步骤
            if step["type"] == "tool":
                result = await self._execute_tool_step(step, agent)
            elif step["type"] == "model":
                result = await self._execute_model_step(step, agent)
            elif step["type"] == "analysis":
                result = await self._execute_analysis_step(step, agent)
            else:
                result = {"error": f"Unknown step type: {step['type']}"}

            # 更新 JobStep 状态
            ended_at = datetime.utcnow()
            duration_ms = int((ended_at - started_at).total_seconds() * 1000)

            with self.db.get_session() as db_session:
                job_step = db_session.query(JobStep).filter_by(id=step_id).first()
                if job_step:
                    job_step.status = "success" if not result.get("error") else "failed"
                    job_step.response_snapshot = json.dumps(result, ensure_ascii=False)
                    job_step.error = result.get("error")
                    job_step.ended_at = ended_at
                    job_step.duration_ms = duration_ms
                    db_session.commit()

            return {
                "step_id": step_id,
                "step_index": step_index,
                "status": "success" if not result.get("error") else "failed",
                "result": result,
                "duration_ms": duration_ms,
            }

        except Exception as e:
            # 更新失败状态
            ended_at = datetime.utcnow()
            duration_ms = int((ended_at - started_at).total_seconds() * 1000)

            with self.db.get_session() as db_session:
                job_step = db_session.query(JobStep).filter_by(id=step_id).first()
                if job_step:
                    job_step.status = "failed"
                    job_step.error = str(e)
                    job_step.ended_at = ended_at
                    job_step.duration_ms = duration_ms
                    db_session.commit()

            return {
                "step_id": step_id,
                "step_index": step_index,
                "status": "failed",
                "error": str(e),
                "duration_ms": duration_ms,
            }

    async def _execute_tool_step(
        self,
        step: Dict[str, Any],
        agent: Dict[str, Any],
    ) -> Dict[str, Any]:
        """执行工具调用步骤

        Args:
            step: 步骤配置
            agent: 智能体配置

        Returns:
            执行结果
        """
        tool_name = step.get("tool")
        params = step.get("params", {})

        # 检查工具是否在允许列表中
        if tool_name not in agent["allowed_tools"]:
            return {"error": f"Tool not allowed: {tool_name}"}

        # 安全检查(这里简化处理,实际应该调用 SecurityGuard)
        # TODO: 集成 SecurityGuard 进行权限检查

        # 执行工具
        if self.tool_executor:
            result = await self.tool_executor(tool_name, params)
            return result
        else:
            return {"message": f"Tool executed: {tool_name}", "params": params}

    async def _execute_model_step(
        self,
        step: Dict[str, Any],
        agent: Dict[str, Any],
    ) -> Dict[str, Any]:
        """执行模型调用步骤

        Args:
            step: 步骤配置
            agent: 智能体配置

        Returns:
            执行结果
        """
        prompt = step.get("prompt", step.get("description", ""))
        provider = agent.get("default_provider") or "bailian"
        model = agent.get("default_model") or "qwen-plus"

        messages = [
            {"role": "system", "content": agent["system_prompt"]},
            {"role": "user", "content": prompt},
        ]

        response = await self.provider_manager.chat(
            provider=provider,
            model=model,
            messages=messages,
        )

        return {"content": response.get("content", "")}

    async def _execute_analysis_step(
        self,
        step: Dict[str, Any],
        agent: Dict[str, Any],
    ) -> Dict[str, Any]:
        """执行分析步骤

        Args:
            step: 步骤配置
            agent: 智能体配置

        Returns:
            分析结果
        """
        # 分析步骤通常是调用 LLM 进行思考和规划
        return await self._execute_model_step(step, agent)

    async def _generate_summary(
        self,
        agent: Dict[str, Any],
        goal: str,
        plan: Dict[str, Any],
        results: List[Dict[str, Any]],
    ) -> str:
        """生成执行总结

        Args:
            agent: 智能体配置
            goal: 用户目标
            plan: 执行计划
            results: 执行结果列表

        Returns:
            总结文本
        """
        summary_prompt = f"""
请总结以下任务的执行情况:

**目标:** {goal}

**执行计划:** {len(plan['steps'])} 个步骤

**执行结果:**
"""
        for idx, result in enumerate(results):
            status = result.get("status", "unknown")
            summary_prompt += f"\n{idx + 1}. {status.upper()}"
            if result.get("error"):
                summary_prompt += f" - 错误: {result['error']}"

        summary_prompt += "\n\n请用简洁的语言总结任务完成情况,包括成功的部分和遇到的问题。"

        provider = agent.get("default_provider") or "bailian"
        model = agent.get("default_model") or "qwen-plus"

        messages = [
            {"role": "system", "content": "你是一个任务总结助手,擅长归纳和总结。"},
            {"role": "user", "content": summary_prompt},
        ]

        try:
            response = await self.provider_manager.chat(
                provider=provider,
                model=model,
                messages=messages,
                temperature=0.5,
            )
            return response.get("content", "执行完成")
        except Exception:
            # 如果总结失败,返回简单总结
            success_count = sum(1 for r in results if r.get("status") == "success")
            total_count = len(results)
            return f"执行了 {total_count} 个步骤,其中 {success_count} 个成功。"

    async def _create_job_run(
        self,
        agent_id: str,
        goal: str,
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """创建 JobRun 记录

        Args:
            agent_id: 智能体ID
            goal: 用户目标
            session_id: 会话ID

        Returns:
            JobRun 字典
        """
        job_id = str(uuid.uuid4())

        with self.db.get_session() as db_session:
            agent = db_session.query(Agent).filter_by(id=agent_id).first()

            job_run = JobRun(
                id=job_id,
                type="agent",
                name=f"{agent.name} - {goal[:50]}",
                status="pending",
                agent_id=agent_id,
                session_id=session_id,
                goal=goal,
            )
            db_session.add(job_run)
            db_session.commit()

            return job_run.to_dict()

    async def _update_job_run(
        self,
        job_id: str,
        updates: Dict[str, Any],
    ) -> None:
        """更新 JobRun 记录

        Args:
            job_id: JobRun ID
            updates: 更新字段字典
        """
        with self.db.get_session() as db_session:
            job_run = db_session.query(JobRun).filter_by(id=job_id).first()
            if job_run:
                for key, value in updates.items():
                    setattr(job_run, key, value)
                db_session.commit()
