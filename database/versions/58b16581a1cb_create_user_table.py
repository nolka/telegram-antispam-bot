"""create_user_table

Revision ID: 58b16581a1cb
Revises: 07fd05d2bde7
Create Date: 2024-12-26 19:40:04.483268

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "58b16581a1cb"
down_revision: Union[str, None] = "07fd05d2bde7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=False),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column("first_name", sa.String),
        sa.Column("last_name", sa.String),
        sa.Column("username", sa.String),
        sa.Column("spam_score", sa.SmallInteger, default=0),
    )


def downgrade() -> None:
    op.drop_table("user")
