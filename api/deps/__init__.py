# This file makes 'deps' a Python package.
# It can also be used to make specific dependencies available at the package level.

from .db import get_db

__all__ = ["get_db"]
