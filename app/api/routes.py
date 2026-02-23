from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.db.models import JobType
from app.db.repo import JobsRepo
from app.services.jobs import JobsService

router = APIRouter()


@router.post("/crawl/hockey", status_code=202)
async def crawl_hockey(session: AsyncSession = Depends(get_session)):
    job_id = await JobsService(session).enqueue(JobType.hockey)
    return {"job_id": job_id}


@router.post("/crawl/oscar", status_code=202)
async def crawl_oscar(session: AsyncSession = Depends(get_session)):
    job_id = await JobsService(session).enqueue(JobType.oscar)
    return {"job_id": job_id}


@router.post("/crawl/all", status_code=202)
async def crawl_all(session: AsyncSession = Depends(get_session)):
    job_id = await JobsService(session).enqueue(JobType.all)
    return {"job_id": job_id}


@router.get("/jobs")
async def list_jobs(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_session),
):
    repo = JobsRepo(session)
    jobs = await repo.list_jobs(limit=limit, offset=offset)
    return [
        {
            "id": j.id,
            "type": j.type,
            "status": j.status,
            "created_at": j.created_at,
            "started_at": j.started_at,
            "finished_at": j.finished_at,
            "error_message": j.error_message,
        }
        for j in jobs
    ]


@router.get("/jobs/{job_id}")
async def get_job(job_id: str, session: AsyncSession = Depends(get_session)):
    repo = JobsRepo(session)
    job = await repo.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {
        "id": job.id,
        "type": job.type,
        "status": job.status,
        "created_at": job.created_at,
        "started_at": job.started_at,
        "finished_at": job.finished_at,
        "error_message": job.error_message,
    }


@router.get("/jobs/{job_id}/results")
async def get_job_results(job_id: str, session: AsyncSession = Depends(get_session)):
    repo = JobsRepo(session)
    job = await repo.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    data = await repo.get_results(job_id)
    return {"job_id": job_id, "type": job.type, "results": data}

@router.get("/results/hockey")
async def results_hockey(
    limit: int = Query(500, ge=1, le=5000),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_session),
):
    repo = JobsRepo(session)
    return await repo.list_hockey_results(limit=limit, offset=offset)

@router.get("/results/oscar")
async def results_oscar(
    limit: int = Query(500, ge=1, le=5000),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_session),
):
    repo = JobsRepo(session)
    return await repo.list_oscar_results(limit=limit, offset=offset)