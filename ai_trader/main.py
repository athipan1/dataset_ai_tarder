from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from ai_trader.config import settings
from ai_trader.db.session import get_db
from sqlalchemy import text

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.PROJECT_VERSION,
    openapi_url="/api/v1/openapi.json"
)

@app.get("/health", tags=["healthcheck"])
async def health_check():
    return {"status": "OK"}

@app.get("/health/db", tags=["healthcheck"])
async def db_health_check(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return {"status": "OK"}
    except Exception as e:
        return {"status": "error", "details": str(e)}
