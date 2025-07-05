from contextvars import ContextVar
from typing import Optional

current_user_id: ContextVar[Optional[int]] = ContextVar("current_user_id", default=None)

def set_current_user_id(user_id: Optional[int]) -> None:
    """Sets the current user's ID in the context."""
    current_user_id.set(user_id)

def get_current_user_id() -> Optional[int]:
    """Gets the current user's ID from the context."""
    return current_user_id.get()

# Example usage (typically in a middleware or request handling logic):
#
# from ai_trader.auth_context import set_current_user_id
#
# async def some_request_handler(request: Request):
#     # Assuming user_id is obtained after authentication
#     user_id = get_user_id_from_request(request) # Replace with actual auth logic
#     token = set_current_user_id(user_id)
#     try:
#         # ... process request ...
#         response = await call_next(request)
#     finally:
#         current_user_id.reset(token) # Reset context var after request
#     return response
#
# Ensure set_current_user_id is called appropriately in your application's
# authentication flow to make the user ID available for audit logging.
# For FastAPI, this could be a dependency that sets the user ID.
#
# Example FastAPI dependency:
#
# from fastapi import Depends, HTTPException, status
# from ai_trader.auth_context import set_current_user_id
#
# async def get_current_active_user(credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())):
#     # Replace with your actual token validation and user extraction logic
#     user = await verify_token_and_get_user(credentials.credentials)
#     if not user:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="Invalid authentication credentials",
#             headers={"WWW-Authenticate": "Bearer"},
#         )
#     set_current_user_id(user.id) # Set the user ID for auditing
#     return user # Return the user object for the endpoint
#
# Then, in your path operations:
# from ai_trader.models import User # Assuming your User model
#
# @app.post("/items/", response_model=Item)
# async def create_item(item: ItemCreate, current_user: User = Depends(get_current_active_user)):
#     # current_user.id is now set in the contextvar
#     # ... your logic to create an item ...
#     pass
