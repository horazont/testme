"""add name column to participant

Revision ID: f2a0c5aa433d
Revises: 93fd28626a19
Create Date: 2021-01-10 17:57:23.411462

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f2a0c5aa433d'
down_revision = '93fd28626a19'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("participant") as bop:
        bop.add_column(
            sa.Column(
                "name",
                sa.Unicode(128),
                nullable=True,
            )
        )
    op.execute(
        "UPDATE participant SET name = 'Namenlos' WHERE name IS NULL"
    )

    with op.batch_alter_table("participant") as bop:
        bop.alter_column(
            "name",
            nullable=False,
        )


def downgrade():
    with op.batch_alter_table("participant") as bop:
        bop.drop_column("name")
