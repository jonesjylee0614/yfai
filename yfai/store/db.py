"""数据库管理模块

使用SQLite存储会话、消息、工具调用、审计日志等数据
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker, Session as SQLSession

Base = declarative_base()


class Session(Base):
    """对话会话表"""

    __tablename__ = "sessions"

    id = Column(String(36), primary_key=True)
    title = Column(String(200), nullable=False, default="新对话")
    assistant_id = Column(String(36), ForeignKey("assistants.id"), nullable=True)
    knowledge_base_id = Column(String(36), ForeignKey("knowledge_bases.id"), nullable=True)
    tags = Column(Text, nullable=True)  # JSON array
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    messages = relationship("Message", back_populates="session", cascade="all, delete-orphan")
    assistant = relationship("Assistant", back_populates="sessions")
    knowledge_base = relationship("KnowledgeBase", back_populates="sessions")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "assistant_id": self.assistant_id,
            "knowledge_base_id": self.knowledge_base_id,
            "tags": json.loads(self.tags) if self.tags else [],
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class Message(Base):
    """对话消息表"""

    __tablename__ = "messages"

    id = Column(String(36), primary_key=True)
    session_id = Column(String(36), ForeignKey("sessions.id"), nullable=False)
    role = Column(String(20), nullable=False)  # user / assistant / system / tool
    content = Column(Text, nullable=False)
    provider = Column(String(50), nullable=True)  # bailian / ollama
    model = Column(String(100), nullable=True)
    message_metadata = Column(Text, nullable=True)  # JSON
    created_at = Column(DateTime, default=datetime.utcnow)

    # 关系
    session = relationship("Session", back_populates="messages")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "session_id": self.session_id,
            "role": self.role,
            "content": self.content,
            "provider": self.provider,
            "model": self.model,
            "metadata": json.loads(self.message_metadata) if self.message_metadata else {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class ToolCall(Base):
    """工具调用记录表"""

    __tablename__ = "tool_calls"

    id = Column(String(36), primary_key=True)
    session_id = Column(String(36), ForeignKey("sessions.id"), nullable=True)
    tool_name = Column(String(100), nullable=False)
    tool_type = Column(String(50), nullable=False)  # mcp / local
    params = Column(Text, nullable=False)  # JSON
    approved_by = Column(String(50), nullable=True)  # user / auto
    risk_level = Column(String(20), nullable=False)  # low / medium / high / critical
    status = Column(String(20), nullable=False)  # pending / approved / rejected / success / failed
    stdout = Column(Text, nullable=True)
    stderr = Column(Text, nullable=True)
    error = Column(Text, nullable=True)
    exit_code = Column(Integer, nullable=True)
    started_at = Column(DateTime, nullable=True)
    ended_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "session_id": self.session_id,
            "tool_name": self.tool_name,
            "tool_type": self.tool_type,
            "params": json.loads(self.params) if self.params else {},
            "approved_by": self.approved_by,
            "risk_level": self.risk_level,
            "status": self.status,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "error": self.error,
            "exit_code": self.exit_code,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Assistant(Base):
    """AI助手配置表"""

    __tablename__ = "assistants"

    id = Column(String(36), primary_key=True)
    name = Column(String(100), nullable=False)
    role = Column(String(200), nullable=True)
    description = Column(Text, nullable=True)
    system_prompt = Column(Text, nullable=False)
    provider = Column(String(50), nullable=True)  # bailian / ollama / auto
    model = Column(String(100), nullable=True)
    tags = Column(Text, nullable=True)  # JSON array
    usage_count = Column(Integer, default=0)
    is_builtin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_used_at = Column(DateTime, nullable=True)

    # 关系
    sessions = relationship("Session", back_populates="assistant")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "role": self.role,
            "description": self.description,
            "system_prompt": self.system_prompt,
            "provider": self.provider,
            "model": self.model,
            "tags": json.loads(self.tags) if self.tags else [],
            "usage_count": self.usage_count,
            "is_builtin": self.is_builtin,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
        }


class KnowledgeBase(Base):
    """知识库配置表"""

    __tablename__ = "knowledge_bases"

    id = Column(String(36), primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    source_type = Column(String(50), nullable=False)  # documents / directory / web / database
    source_config = Column(Text, nullable=False)  # JSON
    embedding_model = Column(String(100), nullable=False)
    chunk_size = Column(Integer, default=500)
    chunk_overlap = Column(Integer, default=50)
    chunk_count = Column(Integer, default=0)
    storage_size = Column(Integer, default=0)  # bytes
    query_count = Column(Integer, default=0)
    indexed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    sessions = relationship("Session", back_populates="knowledge_base")
    chunks = relationship("KnowledgeChunk", back_populates="knowledge_base", cascade="all, delete-orphan")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "source_type": self.source_type,
            "source_config": json.loads(self.source_config) if self.source_config else {},
            "embedding_model": self.embedding_model,
            "chunk_size": self.chunk_size,
            "chunk_overlap": self.chunk_overlap,
            "chunk_count": self.chunk_count,
            "storage_size": self.storage_size,
            "query_count": self.query_count,
            "indexed_at": self.indexed_at.isoformat() if self.indexed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class KnowledgeChunk(Base):
    """知识库分块表"""

    __tablename__ = "knowledge_chunks"

    id = Column(String(36), primary_key=True)
    knowledge_base_id = Column(String(36), ForeignKey("knowledge_bases.id"), nullable=False)
    content = Column(Text, nullable=False)
    source_path = Column(String(500), nullable=True)
    chunk_metadata = Column(Text, nullable=True)  # JSON
    created_at = Column(DateTime, default=datetime.utcnow)

    # 关系
    knowledge_base = relationship("KnowledgeBase", back_populates="chunks")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "knowledge_base_id": self.knowledge_base_id,
            "content": self.content,
            "source_path": self.source_path,
            "metadata": json.loads(self.chunk_metadata) if self.chunk_metadata else {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class KVStore(Base):
    """键值存储表（配置缓存等）"""

    __tablename__ = "kvstore"

    namespace = Column(String(50), primary_key=True)
    key = Column(String(100), primary_key=True)
    value = Column(Text, nullable=False)  # JSON
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Agent(Base):
    """智能体配置表"""

    __tablename__ = "agents"

    id = Column(String(36), primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    system_prompt = Column(Text, nullable=False)
    default_model = Column(String(100), nullable=True)
    default_provider = Column(String(50), nullable=True)  # bailian / ollama / auto
    allowed_tools = Column(Text, nullable=False)  # JSON array
    max_steps = Column(Integer, default=10)
    stop_condition = Column(Text, nullable=True)  # JSON
    is_enabled = Column(Boolean, default=True)
    risk_level = Column(String(20), default="medium")  # low / medium / high
    tags = Column(Text, nullable=True)  # JSON array
    usage_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_used_at = Column(DateTime, nullable=True)

    # 关系
    job_runs = relationship("JobRun", back_populates="agent")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "system_prompt": self.system_prompt,
            "default_model": self.default_model,
            "default_provider": self.default_provider,
            "allowed_tools": json.loads(self.allowed_tools) if self.allowed_tools else [],
            "max_steps": self.max_steps,
            "stop_condition": json.loads(self.stop_condition) if self.stop_condition else None,
            "is_enabled": self.is_enabled,
            "risk_level": self.risk_level,
            "tags": json.loads(self.tags) if self.tags else [],
            "usage_count": self.usage_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
        }


class JobRun(Base):
    """任务运行记录表"""

    __tablename__ = "job_runs"

    id = Column(String(36), primary_key=True)
    type = Column(String(20), nullable=False)  # agent / automation / manual
    name = Column(String(200), nullable=False)
    status = Column(String(20), nullable=False)  # pending / running / success / failed / cancelled
    agent_id = Column(String(36), ForeignKey("agents.id"), nullable=True)
    automation_id = Column(String(36), nullable=True)  # 稍后添加 AutomationTask 表
    session_id = Column(String(36), ForeignKey("sessions.id"), nullable=True)
    goal = Column(Text, nullable=True)  # 用户目标/任务描述
    plan = Column(Text, nullable=True)  # JSON: 计划步骤列表
    summary = Column(Text, nullable=True)
    error = Column(Text, nullable=True)
    started_at = Column(DateTime, nullable=True)
    ended_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # 关系
    agent = relationship("Agent", back_populates="job_runs")
    session = relationship("Session")
    steps = relationship("JobStep", back_populates="job_run", cascade="all, delete-orphan")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "name": self.name,
            "status": self.status,
            "agent_id": self.agent_id,
            "automation_id": self.automation_id,
            "session_id": self.session_id,
            "goal": self.goal,
            "plan": json.loads(self.plan) if self.plan else None,
            "summary": self.summary,
            "error": self.error,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class JobStep(Base):
    """任务步骤记录表"""

    __tablename__ = "job_steps"

    id = Column(String(36), primary_key=True)
    job_id = Column(String(36), ForeignKey("job_runs.id"), nullable=False)
    step_index = Column(Integer, nullable=False)
    step_type = Column(String(50), nullable=False)  # tool / model / fs / shell / connector / etc
    step_name = Column(String(200), nullable=False)
    request_snapshot = Column(Text, nullable=True)  # JSON: 请求参数快照
    response_snapshot = Column(Text, nullable=True)  # JSON: 响应结果快照
    status = Column(String(20), nullable=False)  # pending / running / success / failed / skipped
    approved_by = Column(String(50), nullable=True)  # user / auto / none
    approval_decision = Column(String(20), nullable=True)  # once / permanent / rejected
    error = Column(Text, nullable=True)
    duration_ms = Column(Integer, nullable=True)
    started_at = Column(DateTime, nullable=True)
    ended_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # 关系
    job_run = relationship("JobRun", back_populates="steps")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "job_id": self.job_id,
            "step_index": self.step_index,
            "step_type": self.step_type,
            "step_name": self.step_name,
            "request_snapshot": json.loads(self.request_snapshot) if self.request_snapshot else None,
            "response_snapshot": json.loads(self.response_snapshot) if self.response_snapshot else None,
            "status": self.status,
            "approved_by": self.approved_by,
            "approval_decision": self.approval_decision,
            "error": self.error,
            "duration_ms": self.duration_ms,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class AutomationTask(Base):
    """自动化任务表"""

    __tablename__ = "automation_tasks"

    id = Column(String(36), primary_key=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    trigger_type = Column(String(20), nullable=False)  # cron / interval / once / file / process / webhook
    cron_expr = Column(String(100), nullable=True)  # cron表达式
    interval_seconds = Column(Integer, nullable=True)  # 间隔秒数
    event_config = Column(Text, nullable=True)  # JSON: 事件配置(文件路径、进程名等)
    agent_id = Column(String(36), ForeignKey("agents.id"), nullable=True)
    goal = Column(Text, nullable=True)  # 要执行的目标
    params = Column(Text, nullable=True)  # JSON: 额外参数
    enabled = Column(Boolean, default=True)
    last_run_at = Column(DateTime, nullable=True)
    last_status = Column(String(20), nullable=True)  # success / failed
    run_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关系
    agent = relationship("Agent")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "trigger_type": self.trigger_type,
            "cron_expr": self.cron_expr,
            "interval_seconds": self.interval_seconds,
            "event_config": json.loads(self.event_config) if self.event_config else None,
            "agent_id": self.agent_id,
            "goal": self.goal,
            "params": json.loads(self.params) if self.params else None,
            "enabled": self.enabled,
            "last_run_at": self.last_run_at.isoformat() if self.last_run_at else None,
            "last_status": self.last_status,
            "run_count": self.run_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class Connector(Base):
    """连接器配置表"""

    __tablename__ = "connectors"

    id = Column(String(36), primary_key=True)
    name = Column(String(100), nullable=False)
    type = Column(String(50), nullable=False)  # email / git / http / custom
    description = Column(Text, nullable=True)
    config = Column(Text, nullable=False)  # JSON: 连接配置(URL、认证信息等)
    status = Column(String(20), default="unknown")  # connected / disconnected / error / unknown
    last_test_at = Column(DateTime, nullable=True)
    last_used_at = Column(DateTime, nullable=True)
    use_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "description": self.description,
            "config": json.loads(self.config) if self.config else {},
            "status": self.status,
            "last_test_at": self.last_test_at.isoformat() if self.last_test_at else None,
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
            "use_count": self.use_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class DatabaseManager:
    """数据库管理器"""

    def __init__(self, db_path: str = "data/yfai.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # 创建引擎
        self.engine = create_engine(f"sqlite:///{self.db_path}", echo=False)

        # 创建会话工厂
        self.SessionLocal = sessionmaker(bind=self.engine, autoflush=False, autocommit=False)

        # 创建所有表
        Base.metadata.create_all(self.engine)

    def get_session(self) -> SQLSession:
        """获取数据库会话"""
        return self.SessionLocal()

    def init_builtin_assistants(self) -> None:
        """初始化内置助手"""
        builtin_assistants = [
            {
                "id": "assistant-python",
                "name": "Python 编程助手",
                "role": "🐍 Python专家",
                "description": "专注于Python代码编写、调试和优化",
                "system_prompt": "你是一位资深的Python开发专家，精通Python标准库、第三方库和最佳实践。你的任务是帮助用户编写高质量、可维护的Python代码。",
                "provider": "bailian",
                "model": "qwen-plus",
                "tags": json.dumps(["编程", "Python"]),
                "is_builtin": True,
            },
            {
                "id": "assistant-writer",
                "name": "技术写作助手",
                "role": "✍️ 技术作家",
                "description": "帮助撰写技术文档、博客和说明",
                "system_prompt": "你是一位经验丰富的技术写作专家，擅长将复杂的技术概念用清晰、简洁的语言表达出来。",
                "provider": "bailian",
                "model": "qwen-plus",
                "tags": json.dumps(["写作", "文档"]),
                "is_builtin": True,
            },
            {
                "id": "assistant-translator",
                "name": "中英翻译专家",
                "role": "🌐 专业翻译",
                "description": "准确翻译技术文档和专业内容",
                "system_prompt": "你是一位专业的中英文翻译专家，特别擅长技术领域的翻译。你能准确理解原文的含义，并用地道的目标语言表达。",
                "provider": "bailian",
                "model": "qwen-plus",
                "tags": json.dumps(["翻译", "语言"]),
                "is_builtin": True,
            },
            {
                "id": "assistant-devops",
                "name": "DevOps 运维助手",
                "role": "⚙️ 运维专家",
                "description": "协助系统运维、部署和监控",
                "system_prompt": "你是一位资深的DevOps工程师，精通Linux、Docker、Kubernetes、CI/CD等运维工具和最佳实践。",
                "provider": "ollama",
                "model": "qwen2.5-coder",
                "tags": json.dumps(["运维", "DevOps"]),
                "is_builtin": True,
            },
        ]

        with self.get_session() as session:
            for asst_data in builtin_assistants:
                # 检查是否已存在
                existing = session.query(Assistant).filter_by(id=asst_data["id"]).first()
                if not existing:
                    assistant = Assistant(**asst_data)
                    session.add(assistant)

            session.commit()

    def init_builtin_agents(self) -> None:
        """初始化内置智能体"""
        builtin_agents = [
            {
                "id": "agent-devops",
                "name": "DevOps 助手",
                "description": "能够拉仓库、本地构建、跑单测、压缩日志、生成报告",
                "system_prompt": "你是一位资深的DevOps工程师，精通代码仓库管理、构建流程、测试执行和日志分析。你能帮助用户完成代码拉取、构建、测试和报告生成等任务。",
                "default_model": "qwen2.5-coder",
                "default_provider": "ollama",
                "allowed_tools": json.dumps(["shell.execute", "fs.read_file", "fs.write_file", "fs.list_directory", "process.list", "net.http_request"]),
                "max_steps": 15,
                "risk_level": "medium",
                "tags": json.dumps(["DevOps", "开发", "运维"]),
            },
            {
                "id": "agent-knowledge",
                "name": "知识整理助手",
                "description": "扫描指定目录 Markdown/PDF，分块建库，定期总结变化",
                "system_prompt": "你是一位专业的知识管理专家，擅长文档整理、信息提取和知识归纳。你能帮助用户扫描、索引和总结文档内容。",
                "default_model": "qwen-plus",
                "default_provider": "bailian",
                "allowed_tools": json.dumps(["fs.read_file", "fs.list_directory", "fs.search_files"]),
                "max_steps": 20,
                "risk_level": "low",
                "tags": json.dumps(["知识管理", "文档"]),
            },
            {
                "id": "agent-syscheck",
                "name": "系统巡检助手",
                "description": "定时跑 CPU/RAM/磁盘/网络状态，生成日报写入本地文件",
                "system_prompt": "你是一位专业的系统运维专家，擅长系统监控、性能分析和报告生成。你能帮助用户检查系统状态并生成详细报告。",
                "default_model": "qwen2.5-coder",
                "default_provider": "ollama",
                "allowed_tools": json.dumps(["process.info", "process.list", "net.get_local_ip", "net.check_port", "fs.write_file"]),
                "max_steps": 10,
                "risk_level": "low",
                "tags": json.dumps(["运维", "监控", "系统"]),
            },
        ]

        with self.get_session() as session:
            for agent_data in builtin_agents:
                # 检查是否已存在
                existing = session.query(Agent).filter_by(id=agent_data["id"]).first()
                if not existing:
                    agent = Agent(**agent_data)
                    session.add(agent)

            session.commit()

    def get_stats(self) -> Dict[str, Any]:
        """获取数据库统计信息"""
        with self.get_session() as session:
            return {
                "sessions": session.query(Session).count(),
                "messages": session.query(Message).count(),
                "tool_calls": session.query(ToolCall).count(),
                "assistants": session.query(Assistant).count(),
                "knowledge_bases": session.query(KnowledgeBase).count(),
                "agents": session.query(Agent).count(),
                "job_runs": session.query(JobRun).count(),
                "job_steps": session.query(JobStep).count(),
                "automation_tasks": session.query(AutomationTask).count(),
                "connectors": session.query(Connector).count(),
            }

