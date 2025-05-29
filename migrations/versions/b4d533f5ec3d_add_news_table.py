"""add_news_table

Revision ID: b4d533f5ec3d
Revises: f5b345f33ac4
Create Date: 2025-05-29 15:40:05.141207

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b4d533f5ec3d'
down_revision: Union[str, None] = 'f5b345f33ac4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
