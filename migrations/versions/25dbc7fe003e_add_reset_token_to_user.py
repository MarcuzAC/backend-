"""add_reset_token_to_user

Revision ID: 25dbc7fe003e
Revises: 4fff68ce738a
Create Date: 2025-03-14 13:10:26.083396

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '25dbc7fe003e'
down_revision: Union[str, None] = '4fff68ce738a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('users', sa.Column('reset_token', sa.String(), nullable=True))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('users', 'reset_token')
    # ### end Alembic commands ###
