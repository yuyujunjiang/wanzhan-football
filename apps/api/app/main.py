from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.settings import settings
from app.domain.results.scheduler import start_matches_scheduler, stop_matches_scheduler
from app.routes.ai import router as ai_router
from app.routes.auth import router as auth_router
from app.routes.ledger import router as ledger_router
from app.routes.matches import router as matches_router
from app.routes.tickets import router as tickets_router


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    scheduler_task = start_matches_scheduler()
    try:
        yield
    finally:
        await stop_matches_scheduler(scheduler_task)


app = FastAPI(lifespan=lifespan)

_default_cors = {
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://0.0.0.0:3000",
    "http://10.21.179.19:3000",
}
_cors_origins = [
    origin.strip()
    for origin in settings.cors_origins.split(",")
    if origin.strip()
] or list(_default_cors)

# Allow the Next.js dev server to call the API from browsers.
# Without CORS, the browser often surfaces this as "Failed to fetch".
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(tickets_router)
app.include_router(matches_router)
app.include_router(ledger_router)
app.include_router(auth_router)
app.include_router(ai_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
