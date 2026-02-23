import json
import logging
import aio_pika

from app.core.config import get_settings
from app.queue.messages import CrawlMessage

log = logging.getLogger("publisher")


async def publish_job(msg: CrawlMessage) -> None:
    settings = get_settings()
    connection = await aio_pika.connect_robust(settings.rabbitmq_url)
    try:
        channel = await connection.channel()
        await channel.declare_queue(settings.queue_name, durable=True)

        body = msg.model_dump_json().encode()
        message = aio_pika.Message(
            body=body,
            content_type="application/json",
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
        )
        await channel.default_exchange.publish(message, routing_key=settings.queue_name)
        log.info("published job=%s type=%s", msg.job_id, msg.job_type)
    finally:
        await connection.close()