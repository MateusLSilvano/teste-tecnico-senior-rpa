from fastapi import FastAPI

from app.api.routes import router
from app.core.logging import setup_logging
from app.db.init_db import init_models


def create_app() -> FastAPI:
    setup_logging()
    app = FastAPI(title="Senior RPA Test", version="1.0.0")
    app.include_router(router)

    @app.on_event("startup")
    async def _startup():
        await init_models()

    return app


app = create_app()