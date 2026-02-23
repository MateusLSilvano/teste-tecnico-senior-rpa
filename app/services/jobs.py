import logging
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import JobType
from app.db.repo import JobsRepo
from app.queue.messages import CrawlMessage
from app.queue.publisher import publish_job

log = logging.getLogger("jobs_service")


class JobsService:
    def __init__(self, session: AsyncSession):
        self.repo = JobsRepo(session)

    async def enqueue(self, job_type: JobType) -> str:
        job = await self.repo.create_job(job_type)
        await publish_job(CrawlMessage(job_id=job.id, job_type=job.type))
        log.info("enqueued job=%s type=%s", job.id, job.type)
        return job.id