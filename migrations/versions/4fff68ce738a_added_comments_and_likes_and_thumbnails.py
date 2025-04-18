"""added comments and likes and thumbnails

Revision ID: 4fff68ce738a
Revises: 3f0a0304568b
Create Date: 2025-03-12 14:50:46.635809

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4fff68ce738a'
down_revision: Union[str, None] = '3f0a0304568b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('videos', sa.Column('thumbnail_url', sa.String(), nullable=True))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('videos', 'thumbnail_url')
    # ### end Alembic commands ###
