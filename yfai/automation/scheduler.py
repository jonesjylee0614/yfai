"""自动化调度器模块

负责定时任务、事件触发等自动化功能
"""

import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Callable
from pathlib import Path
import logging

from yfai.store.db import DatabaseManager, AutomationTask, Agent

logger = logging.getLogger(__name__)


class AutomationScheduler:
    """自动化调度器

    支持:
    1. Cron 表达式调度
    2. 固定间隔调度
    3. 一次性任务
    4. 文件监听触发
    5. 进程状态触发
    """

    def __init__(
        self,
        db_manager: DatabaseManager,
        agent_runner_func: Callable,
    ):
        """初始化调度器

        Args:
            db_manager: 数据库管理器
            agent_runner_func: 智能体运行函数
        """
        self.db = db_manager
        self.agent_runner_func = agent_runner_func
        self.running = False
        self.tasks: Dict[str, asyncio.Task] = {}

    async def start(self):
        """启动调度器"""
        logger.info("Starting automation scheduler...")
        self.running = True

        # 加载所有启用的任务
        await self._load_and_schedule_tasks()

        # 启动主调度循环
        asyncio.create_task(self._main_loop())

    async def stop(self):
        """停止调度器"""
        logger.info("Stopping automation scheduler...")
        self.running = False

        # 取消所有运行中的任务
        for task in self.tasks.values():
            task.cancel()

    async def _main_loop(self):
        """主调度循环"""
        while self.running:
            try:
                await asyncio.sleep(60)  # 每分钟检查一次
                await self._check_and_trigger_tasks()
            except Exception as e:
                logger.error(f"Scheduler loop error: {e}")

    async def _load_and_schedule_tasks(self):
        """加载并调度所有启用的任务"""
        with self.db.get_session() as db_session:
            tasks = db_session.query(AutomationTask).filter_by(enabled=True).all()

            for task in tasks:
                await self._schedule_task(task.to_dict())

    async def _schedule_task(self, task: Dict[str, Any]):
        """调度单个任务"""
        task_id = task["id"]
        trigger_type = task["trigger_type"]

        if trigger_type == "interval":
            # 间隔调度
            interval_seconds = task.get("interval_seconds", 3600)
            asyncio.create_task(self._interval_task(task_id, interval_seconds))
        elif trigger_type == "cron":
            # Cron 调度(简化实现)
            logger.info(f"Cron task {task_id} scheduled (not fully implemented)")
        elif trigger_type == "once":
            # 一次性任务
            asyncio.create_task(self._execute_automation_task(task_id))

    async def _interval_task(self, task_id: str, interval_seconds: int):
        """间隔任务执行"""
        while self.running:
            try:
                # 检查任务是否仍然启用
                with self.db.get_session() as db_session:
                    task = db_session.query(AutomationTask).filter_by(id=task_id).first()
                    if not task or not task.enabled:
                        logger.info(f"Task {task_id} disabled, stopping interval task")
                        break

                # 执行任务
                await self._execute_automation_task(task_id)

                # 等待间隔
                await asyncio.sleep(interval_seconds)
            except Exception as e:
                logger.error(f"Interval task {task_id} error: {e}")
                await asyncio.sleep(60)  # 错误后等待1分钟再重试

    async def _check_and_trigger_tasks(self):
        """检查并触发需要执行的任务"""
        # 这里可以实现更复杂的触发逻辑
        pass

    async def _execute_automation_task(self, task_id: str):
        """执行自动化任务"""
        try:
            with self.db.get_session() as db_session:
                task = db_session.query(AutomationTask).filter_by(id=task_id).first()
                if not task:
                    logger.error(f"Task {task_id} not found")
                    return

                agent_id = task.agent_id
                goal = task.goal

                if not agent_id or not goal:
                    logger.error(f"Task {task_id} missing agent_id or goal")
                    return

                logger.info(f"Executing automation task: {task.name}")

                # 更新最后运行时间
                task.last_run_at = datetime.utcnow()
                task.run_count += 1
                db_session.commit()

            # 运行智能体
            result = await self.agent_runner_func(agent_id, goal)

            # 更新任务状态
            with self.db.get_session() as db_session:
                task = db_session.query(AutomationTask).filter_by(id=task_id).first()
                if task:
                    task.last_status = result.get("status", "unknown")
                    db_session.commit()

            logger.info(f"Automation task {task_id} completed: {result.get('status')}")

        except Exception as e:
            logger.error(f"Failed to execute automation task {task_id}: {e}")

            # 更新失败状态
            with self.db.get_session() as db_session:
                task = db_session.query(AutomationTask).filter_by(id=task_id).first()
                if task:
                    task.last_status = "failed"
                    db_session.commit()

    async def trigger_task_manually(self, task_id: str) -> Dict[str, Any]:
        """手动触发任务

        Args:
            task_id: 任务ID

        Returns:
            执行结果
        """
        await self._execute_automation_task(task_id)
        return {"status": "triggered", "task_id": task_id}
