from fastapi import FastAPI

from app.routes.matches import router as matches_router
from app.routes.tickets import router as tickets_router


app = FastAPI()
app.include_router(tickets_router)
app.include_router(matches_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}

