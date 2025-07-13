import datetime
from typing import Optional

from sqlalchemy import Boolean, Column, DateTime
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class SoftDeleteMixin:
    is_deleted = Column(Boolean, default=False, nullable=False, index=True)
    deleted_at = Column(DateTime, nullable=True, index=True)

    def soft_delete(self):
        self.is_deleted = True
        self.deleted_at = datetime.datetime.now(datetime.timezone.utc)
