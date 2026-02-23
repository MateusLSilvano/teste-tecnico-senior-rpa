# app/queue/consumer.py
import asyncio
import json
import logging

import aio_pika
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import setup_logging
from app.crawlers.hockey import fetch_hockey
from app.crawlers.oscar import fetch_oscar
from app.db.init_db import init_models
from app.db.repo import JobsRepo
from app.db.session import SessionLocal
from app.queue.messages import CrawlMessage
from app.db.models import JobType

log = logging.getLogger("worker")


async def _connect_rabbitmq_with_retry(url: str) -> aio_pika.RobustConnection:
    delay = 1.0
    while True:
        try:
            conn = await aio_pika.connect_robust(url, timeout=5)
            log.info("connected to rabbitmq: %s", url)
            return conn
        except Exception as e:
            log.warning("rabbitmq not ready (%s). retrying in %.1fs", e, delay)
            await asyncio.sleep(delay)
            delay = min(delay * 1.5, 10.0)


async def _process_message(msg: aio_pika.IncomingMessage) -> None:
    async with msg.process(requeue=False):
        payload = json.loads(msg.body.decode("utf-8"))
        cm = CrawlMessage.model_validate(payload)

        async with SessionLocal() as session:  # type: AsyncSession
            repo = JobsRepo(session)

            await repo.mark_running(cm.job_id)
            try:
                if cm.job_type == JobType.hockey:
                    hockey_rows = await fetch_hockey()
                    await repo.replace_hockey_results(cm.job_id, hockey_rows)

                elif cm.job_type == JobType.oscar:
                    oscar_rows = await fetch_oscar()
                    await repo.replace_oscar_results(cm.job_id, oscar_rows)

                elif cm.job_type == JobType.all:
                    hockey_rows = await fetch_hockey()
                    await repo.replace_hockey_results(cm.job_id, hockey_rows)

                    oscar_rows = await fetch_oscar()
                    await repo.replace_oscar_results(cm.job_id, oscar_rows)

                else:
                    raise ValueError(f"Unsupported job type: {cm.job_type}")

                await repo.mark_completed(cm.job_id)
                log.info("completed job=%s type=%s", cm.job_id, cm.job_type)

            except Exception as e:
                await repo.mark_failed(cm.job_id, str(e))
                log.exception("failed job=%s type=%s", cm.job_id, cm.job_type)
                raise


async def run_worker() -> None:
    setup_logging()
    settings = get_settings()
    await init_models()

    connection = await _connect_rabbitmq_with_retry(settings.rabbitmq_url)

    channel = await connection.channel()
    await channel.set_qos(prefetch_count=1)

    queue = await channel.declare_queue(settings.queue_name, durable=True)
    log.info("worker up. queue=%s", settings.queue_name)

    await queue.consume(_process_message)

    try:
        while True:
            await asyncio.sleep(3600)
    finally:
        await connection.close()


if __name__ == "__main__":
    asyncio.run(run_worker())