import enum
import uuid
from datetime import datetime
from sqlalchemy import (
    String,
    DateTime,
    Enum,
    Integer,
    Boolean,
    ForeignKey,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class JobType(str, enum.Enum):
    hockey = "hockey"
    oscar = "oscar"
    all = "all"


class JobStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    type: Mapped[JobType] = mapped_column(Enum(JobType), nullable=False)
    status: Mapped[JobStatus] = mapped_column(Enum(JobStatus), nullable=False, default=JobStatus.pending)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.utcnow())
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String, nullable=True)

    hockey_results: Mapped[list["HockeyResult"]] = relationship(back_populates="job", cascade="all, delete-orphan")
    oscar_results: Mapped[list["OscarResult"]] = relationship(back_populates="job", cascade="all, delete-orphan")


class HockeyResult(Base):
    __tablename__ = "hockey_results"
    __table_args__ = (
        UniqueConstraint("job_id", "team_name", "year", name="uq_hockey_job_team_year"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), index=True, nullable=False)

    team_name: Mapped[str] = mapped_column(String, nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    wins: Mapped[int] = mapped_column(Integer, nullable=False)
    losses: Mapped[int] = mapped_column(Integer, nullable=False)
    ot_losses: Mapped[int] = mapped_column(Integer, nullable=False)
    win_pct: Mapped[str] = mapped_column(String, nullable=False)
    goals_for: Mapped[int] = mapped_column(Integer, nullable=False)
    goals_against: Mapped[int] = mapped_column(Integer, nullable=False)
    goal_diff: Mapped[int] = mapped_column(Integer, nullable=False)

    job: Mapped[Job] = relationship(back_populates="hockey_results")


class OscarResult(Base):
    __tablename__ = "oscar_results"
    __table_args__ = (
        UniqueConstraint("job_id", "title", "year", name="uq_oscar_job_title_year"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), index=True, nullable=False)

    year: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    nominations: Mapped[int] = mapped_column(Integer, nullable=False)
    awards: Mapped[int] = mapped_column(Integer, nullable=False)
    best_picture: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    job: Mapped[Job] = relationship(back_populates="oscar_results")