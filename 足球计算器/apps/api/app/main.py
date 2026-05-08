from fastapi import FastAPI

from app.routes.tickets import router as tickets_router


app = FastAPI()
app.include_router(tickets_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}

