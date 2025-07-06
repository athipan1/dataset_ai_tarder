from fastapi import FastAPI

from api.routers import users, trades, strategies, analytics

app = FastAPI(
    title="AI Trader API",
    description="API for managing trading strategies, trades, users, and analytics.",
    version="0.1.0",
    # You can add more metadata here, like terms_of_service, contact, license_info
    # openapi_tags can be used to add descriptions to your tags
    openapi_tags=[
        {
            "name": "users",
            "description": "Operations with users. The **login** logic is also here.",
        },
        {
            "name": "trades",
            "description": "Manage trades.",
        },
        {
            "name": "strategies",
            "description": "Manage trading strategies.",
        },
        {
            "name": "analytics",
            "description": "Manage trade analytics data.",
        },
    ],
)

# Include routers
# It's common to prefix API routes with /api/v1 or similar
app.include_router(users.router, prefix="/api/v1/users", tags=["users"])
app.include_router(trades.router, prefix="/api/v1/trades", tags=["trades"])
app.include_router(strategies.router, prefix="/api/v1/strategies", tags=["strategies"])
app.include_router(analytics.router, prefix="/api/v1/analytics", tags=["analytics"])


@app.get("/", tags=["root"])  # E302 fixed
async def root():
    return {"message": "Welcome to AI Trader API. Visit /docs for API documentation."}


# Optional: Add custom exception handlers, middleware, etc.
# For example, to handle SQLAlchemy errors globally:
# from sqlalchemy.exc import SQLAlchemyError
# from fastapi import Request, status
# from fastapi.responses import JSONResponse

# @app.exception_handler(SQLAlchemyError)
# async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
#     # Log the error for debugging
#     print(f"SQLAlchemyError: {exc}") # Replace with proper logging
#     return JSONResponse(
#         status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#         content={"detail": "An internal database error occurred."},
#     )
