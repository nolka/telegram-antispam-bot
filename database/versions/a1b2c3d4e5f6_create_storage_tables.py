"""create_confirmed_user, confirm_code, spam_training tables

Revision ID: a1b2c3d4e5f6
Revises: 0c4aa62f3465
Create Date: 2025-01-06 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "0c4aa62f3465"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "confirmed_user",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("group_id", sa.BigInteger, nullable=False),
        sa.Column("user_id", sa.BigInteger, nullable=False),
        sa.UniqueConstraint("group_id", "user_id", name="uq_confirmed_user_group_user"),
    )

    op.create_table(
        "confirm_code",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("group_id", sa.BigInteger, nullable=False),
        sa.Column("user_id", sa.BigInteger, nullable=False),
        sa.Column("code", sa.String, nullable=False),
        sa.UniqueConstraint("group_id", "user_id", name="uq_confirm_code_group_user"),
    )

    op.create_table(
        "spam_training",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("is_spam", sa.Boolean, nullable=False),
        sa.Column("text", sa.Text, nullable=False),
    )


def downgrade() -> None:
    op.drop_table("spam_training")
    op.drop_table("confirm_code")
    op.drop_table("confirmed_user")
