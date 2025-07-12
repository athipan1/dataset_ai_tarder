from fastapi import FastAPI
from ai_trader.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.PROJECT_VERSION,
    openapi_url="/api/v1/openapi.json"
)

@app.get("/health", tags=["healthcheck"])
async def health_check():
    return {"status": "OK"}
