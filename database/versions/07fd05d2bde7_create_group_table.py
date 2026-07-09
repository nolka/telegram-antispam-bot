"""create_channels_table

Revision ID: 07fd05d2bde7
Revises:
Create Date: 2024-12-26 16:03:29.308795

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "07fd05d2bde7"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "group",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=False),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column("name", sa.String, nullable=True),
        sa.Column("description", sa.String, nullable=True),
        sa.Column("type", sa.String, nullable=True),  # public, private, etc
    )


def downgrade() -> None:
    op.drop_table("group")
