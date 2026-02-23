from pydantic import BaseModel, Field
from app.db.models import JobType


class CrawlMessage(BaseModel):
    job_id: str = Field(min_length=1)
    job_type: JobType