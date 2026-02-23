# app/tests/integration/test_end_to_end_hockey.py
from __future__ import annotations

import asyncio
import os
import sys
import time
from typing import Callable, Awaitable

import pytest
import httpx
from testcontainers.postgres import PostgresContainer
from testcontainers.rabbitmq import RabbitMqContainer


def _purge_app_modules() -> None:
    """
    Garantia de "fresh import" com env vars novas.
    Evita engine/settings ficarem cacheados entre testes.
    """
    prefixes = (
        "app.core.config",
        "app.db",
        "app.api",
        "app.services",
        "app.queue",
        "app.main",
    )
    for name in list(sys.modules.keys()):
        if name == "app" or name.startswith(prefixes):
            sys.modules.pop(name, None)


def _pg_async_url(pg_host: str, pg_port: int, user: str, password: str, db: str) -> str:
    # sslmode=disable evita asyncpg tentar SSL em ambientes locais
    return f"postgresql+asyncpg://{user}:{password}@{pg_host}:{pg_port}/{db}"


def _rabbit_url(host: str, port: int, user: str = "guest", password: str = "guest") -> str:
    return f"amqp://{user}:{password}@{host}:{port}/"


async def _eventually(
    assertion: Callable[[], Awaitable[None]],
    timeout_s: float = 10.0,
    interval_s: float = 0.25,
) -> None:
    deadline = time.monotonic() + timeout_s
    last_exc: BaseException | None = None
    while time.monotonic() < deadline:
        try:
            await assertion()
            return
        except BaseException as exc:
            last_exc = exc
            await asyncio.sleep(interval_s)
    if last_exc:
        raise last_exc
    raise AssertionError("Condition not met in time")


@pytest.mark.asyncio
async def test_hockey_flow_end_to_end(monkeypatch: pytest.MonkeyPatch) -> None:
    DB_USER = "test"
    DB_PASS = "test"
    DB_NAME = "test"

    # IMPORTANTÍSSIMO no Rabbit: força a porta AMQP (5672)
    # (isso reduz muito aqueles logs de "Incompatible Protocol Versions")
    with PostgresContainer(
        "postgres:16-alpine",
        username=DB_USER,
        password=DB_PASS,
        dbname=DB_NAME,
    ) as pg, RabbitMqContainer("rabbitmq:3-alpine", port=5672) as rb:

        pg_host = pg.get_container_host_ip()
        pg_port = int(pg.get_exposed_port(5432))

        rb_host = rb.get_container_host_ip()
        rb_port = int(rb.get_exposed_port(5672))

        os.environ["DATABASE_URL"] = _pg_async_url(pg_host, pg_port, DB_USER, DB_PASS, DB_NAME)
        os.environ["RABBITMQ_URL"] = _rabbit_url(rb_host, rb_port)
        os.environ["QUEUE_NAME"] = "crawl_jobs"
        os.environ["LOG_LEVEL"] = "INFO"

        _purge_app_modules()

        # Imports só depois de env setado
        from app.core.config import get_settings
        get_settings.cache_clear()

        from app.main import create_app
        import app.queue.consumer as consumer_mod
        from app.db.init_db import init_models
        import app.crawlers.hockey as hockey_mod

        async def fake_fetch_hockey(max_pages: int = 50):
            return [
                {
                    "team_name": "Boston Bruins",
                    "year": 1990,
                    "wins": 44,
                    "losses": 24,
                    "ot_losses": 0,
                    "win_pct": "0.55",
                    "goals_for": 299,
                    "goals_against": 264,
                    "goal_diff": 35,
                }
            ]

        monkeypatch.setattr(consumer_mod, "fetch_hockey", fake_fetch_hockey, raising=False)

        # se o consumer tiver um registry/dict de handlers, atualiza também
        for name in ("CRAWLERS", "HANDLERS", "JOB_HANDLERS", "DISPATCH", "ROUTES"):
            reg = getattr(consumer_mod, name, None)
            if isinstance(reg, dict):
                # tenta com JobType do próprio consumer (mais seguro)
                jt = getattr(consumer_mod, "JobType", None)
                if jt is not None and getattr(jt, "hockey", None) in reg:
                    reg[jt.hockey] = fake_fetch_hockey

        # Garante schema antes de qualquer request
        await init_models()

        app = create_app()

        worker_task = asyncio.create_task(consumer_mod.run_worker())
        try:
            # httpx "senior mode": ASGITransport (sem deprecation do app=)
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                r = await client.post("/crawl/hockey")
                assert r.status_code == 202
                job_id = r.json()["job_id"]

                async def _assert_completed_and_has_results() -> None:
                    j = await client.get(f"/jobs/{job_id}")
                    assert j.status_code == 200
                    assert j.json()["status"] == "completed"

                    rr = await client.get(f"/jobs/{job_id}/results")
                    assert rr.status_code == 200
                    data = rr.json()["results"]["hockey"]
                    assert len(data) == 1
                    assert data[0]["team_name"] == "Boston Bruins"

                await _eventually(_assert_completed_and_has_results, timeout_s=15.0, interval_s=0.3)

        finally:
            worker_task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await worker_task