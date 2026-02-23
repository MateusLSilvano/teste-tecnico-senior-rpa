from __future__ import annotations

from datetime import datetime
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Job, JobStatus, JobType, HockeyResult, OscarResult


class JobsRepo:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_job(self, job_type: JobType) -> Job:
        job = Job(type=job_type, status=JobStatus.pending)
        self.session.add(job)
        await self.session.commit()
        await self.session.refresh(job)
        return job

    async def get_job(self, job_id: str) -> Job | None:
        res = await self.session.execute(select(Job).where(Job.id == job_id))
        return res.scalar_one_or_none()

    async def list_jobs(self, limit: int = 50, offset: int = 0) -> list[Job]:
        res = await self.session.execute(
            select(Job).order_by(Job.created_at.desc()).limit(limit).offset(offset)
        )
        return list(res.scalars().all())

    async def mark_running(self, job_id: str) -> None:
        job = await self.get_job(job_id)
        if not job:
            return
        job.status = JobStatus.running
        job.started_at = datetime.utcnow()
        await self.session.commit()

    async def mark_completed(self, job_id: str) -> None:
        job = await self.get_job(job_id)
        if not job:
            return
        job.status = JobStatus.completed
        job.finished_at = datetime.utcnow()
        job.error_message = None
        await self.session.commit()

    async def mark_failed(self, job_id: str, error: str) -> None:
        job = await self.get_job(job_id)
        if not job:
            return
        job.status = JobStatus.failed
        job.finished_at = datetime.utcnow()
        job.error_message = (error or "")[:2000]
        await self.session.commit()

    async def replace_hockey_results(self, job_id: str, rows: list[dict]) -> None:
        # NÃO acessa job.hockey_results (lazy load) -> MissingGreenlet
        job = await self.get_job(job_id)
        if not job:
            return

        await self.session.execute(
            delete(HockeyResult).where(HockeyResult.job_id == job_id)
        )

        self.session.add_all([HockeyResult(job_id=job_id, **r) for r in rows])
        await self.session.commit()

    async def replace_oscar_results(self, job_id: str, rows: list[dict]) -> None:
        job = await self.get_job(job_id)
        if not job:
            return

        await self.session.execute(
            delete(OscarResult).where(OscarResult.job_id == job_id)
        )

        self.session.add_all([OscarResult(job_id=job_id, **r) for r in rows])
        await self.session.commit()

    async def get_results(self, job_id: str) -> dict:
        # Query direto, sem relationship lazy
        job = await self.get_job(job_id)
        if not job:
            return {"hockey": [], "oscar": []}

        h_res = await self.session.execute(
            select(HockeyResult).where(HockeyResult.job_id == job_id).order_by(HockeyResult.id.asc())
        )
        o_res = await self.session.execute(
            select(OscarResult).where(OscarResult.job_id == job_id).order_by(OscarResult.id.asc())
        )

        hockey = [
            {
                "team_name": r.team_name,
                "year": r.year,
                "wins": r.wins,
                "losses": r.losses,
                "ot_losses": r.ot_losses,
                "win_pct": r.win_pct,
                "goals_for": r.goals_for,
                "goals_against": r.goals_against,
                "goal_diff": r.goal_diff,
            }
            for r in h_res.scalars().all()
        ]

        oscar = [
            {
                "year": r.year,
                "title": r.title,
                "nominations": r.nominations,
                "awards": r.awards,
                "best_picture": r.best_picture,
            }
            for r in o_res.scalars().all()
        ]

        return {"hockey": hockey, "oscar": oscar}
    
    async def list_hockey_results(self, limit: int = 500, offset: int = 0) -> list[dict]:
        res = await self.session.execute(
            select(HockeyResult).order_by(HockeyResult.year.asc(), HockeyResult.team_name.asc()).limit(limit).offset(offset)
        )
        return [
            {
                "job_id": r.job_id,
                "team_name": r.team_name,
                "year": r.year,
                "wins": r.wins,
                "losses": r.losses,
                "ot_losses": r.ot_losses,
                "win_pct": r.win_pct,
                "goals_for": r.goals_for,
                "goals_against": r.goals_against,
                "goal_diff": r.goal_diff,
            }
            for r in res.scalars().all()
        ]

    async def list_oscar_results(self, limit: int = 500, offset: int = 0) -> list[dict]:
        res = await self.session.execute(
            select(OscarResult).order_by(OscarResult.year.asc(), OscarResult.title.asc()).limit(limit).offset(offset)
        )
        return [
            {
                "job_id": r.job_id,
                "year": r.year,
                "title": r.title,
                "nominations": r.nominations,
                "awards": r.awards,
                "best_picture": r.best_picture,
            }
            for r in res.scalars().all()
        ]