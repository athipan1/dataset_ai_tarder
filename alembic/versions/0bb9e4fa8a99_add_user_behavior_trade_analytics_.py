"""add user_behavior, trade_analytics, market_event models with renamed metadata column

Revision ID: 0bb9e4fa8a99
Revises: aef0e2350ba4
Create Date: 2025-07-05 18:25:57.710206

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0bb9e4fa8a99'
down_revision: Union[str, Sequence[str], None] = 'aef0e2350ba4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
