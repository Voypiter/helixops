"""SQLAlchemy ORM models for persistence."""

from datetime import datetime
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, JSON, ForeignKey, Index
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship


Base = declarative_base()


class WorkflowModel(Base):
    """Persistent workflow definition."""
    __tablename__ = "workflows"

    workflow_id = Column(String(255), primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(String(1000), nullable=True)
    definition = Column(JSON, nullable=False)  # Full workflow JSON
    created_at = Column(DateTime, default=datetime.utcnow)
    metadata_json = Column(JSON, nullable=True)

    runs = relationship("ExecutionRunModel", back_populates="workflow")

    __table_args__ = (
        Index("idx_workflow_name", "name"),
    )


class ExecutionRunModel(Base):
    """Persistent execution run."""
    __tablename__ = "execution_runs"

    run_id = Column(String(255), primary_key=True)
    workflow_id = Column(String(255), ForeignKey("workflows.workflow_id"), nullable=False)
    state = Column(String(50), nullable=False)  # PENDING, RUNNING, SUCCEEDED, FAILED
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    total_duration_ms = Column(Float, nullable=True)
    succeeded = Column(Boolean, default=False)
    error_message = Column(String(1000), nullable=True)
    metadata_json = Column(JSON, nullable=True)

    workflow = relationship("WorkflowModel", back_populates="runs")
    task_attempts = relationship("TaskAttemptModel", back_populates="run")
    events = relationship("ExecutionEventModel", back_populates="run")

    __table_args__ = (
        Index("idx_run_workflow", "workflow_id"),
        Index("idx_run_created", "created_at"),
    )


class TaskAttemptModel(Base):
    """Persistent task execution attempt."""
    __tablename__ = "task_attempts"

    attempt_id = Column(String(255), primary_key=True)
    run_id = Column(String(255), ForeignKey("execution_runs.run_id"), nullable=False)
    task_id = Column(String(255), nullable=False)
    attempt_number = Column(Integer, nullable=False)
    state = Column(String(50), nullable=False)  # PENDING, RUNNING, SUCCEEDED, FAILED
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    duration_ms = Column(Float, nullable=True)
    succeeded = Column(Boolean, default=False)
    error_message = Column(String(1000), nullable=True)
    output_payload = Column(JSON, nullable=True)
    failure_class = Column(String(50), nullable=True)  # TRANSIENT, PERMANENT, TIMEOUT, etc.
    was_skipped = Column(Boolean, default=False)
    was_cancelled = Column(Boolean, default=False)
    was_timed_out = Column(Boolean, default=False)
    metadata_json = Column(JSON, nullable=True)

    run = relationship("ExecutionRunModel", back_populates="task_attempts")
    events = relationship("ExecutionEventModel", back_populates="task_attempt")

    __table_args__ = (
        Index("idx_attempt_run", "run_id"),
        Index("idx_attempt_task", "task_id"),
        Index("idx_attempt_state", "state"),
    )


class ExecutionEventModel(Base):
    """Persistent execution event."""
    __tablename__ = "execution_events"

    event_id = Column(String(255), primary_key=True)
    run_id = Column(String(255), ForeignKey("execution_runs.run_id"), nullable=False)
    attempt_id = Column(
        String(255),
        ForeignKey("task_attempts.attempt_id"),
        nullable=True,
    )
    event_type = Column(String(100), nullable=False)  # TASK_RUNNING, TASK_SUCCEEDED, etc.
    task_id = Column(String(255), nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    duration_ms = Column(Float, nullable=True)
    error_message = Column(String(1000), nullable=True)
    metadata_json = Column(JSON, nullable=True)

    run = relationship("ExecutionRunModel", back_populates="events")
    task_attempt = relationship("TaskAttemptModel", back_populates="events")

    __table_args__ = (
        Index("idx_event_run", "run_id"),
        Index("idx_event_type", "event_type"),
        Index("idx_event_timestamp", "timestamp"),
    )
