"""create_message_table

Revision ID: 0c4aa62f3465
Revises: 58b16581a1cb
Create Date: 2024-12-26 20:23:29.805419

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0c4aa62f3465"
down_revision: Union[str, None] = "58b16581a1cb"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "message",
        sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=False),
        sa.Column(
            "group_id", sa.BigInteger, sa.ForeignKey("group.id"), primary_key=True, index=True
        ),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column("user_id", sa.BigInteger, sa.ForeignKey("user.id"), index=True, nullable=False),
        sa.Column("type", sa.String, nullable=False),  # message, photo, voice, audio, etc
        sa.Column("text", sa.String),
        sa.Column("params", sa.JSON),
        sa.Column("spam_score", sa.SmallInteger, default=0),
    )

    op.create_table(
        "disabled_word",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("term", sa.String, nullable=False),
        sa.Column("rule_type", sa.String, nullable=False),  # plain, regex
        sa.Column("spam_score", sa.SmallInteger, default=0),
    )

    # Composite index for fast message count queries by user in a group
    op.create_index("ix_message_group_user", "message", ["group_id", "user_id"], unique=False)


def downgrade() -> None:
    op.drop_table("message")
    op.drop_table("disabled_word")
