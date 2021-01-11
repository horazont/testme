"""add allow_none column to question

Revision ID: 93fd28626a19
Revises: 9626a4485615
Create Date: 2021-01-10 17:33:49.084230

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '93fd28626a19'
down_revision = '9626a4485615'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("question") as bop:
        bop.add_column(
            sa.Column(
                "allow_none",
                sa.Boolean(),
                nullable=True,
            )
        )
    op.execute(
        "UPDATE question SET allow_none = 0 WHERE allow_none IS NULL"
    )

    with op.batch_alter_table("question") as bop:
        bop.alter_column(
            "allow_none",
            nullable=False,
        )


def downgrade():
    with op.batch_alter_table("question") as bop:
        bop.drop_column("allow_none")
