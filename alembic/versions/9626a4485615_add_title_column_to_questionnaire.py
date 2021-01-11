"""
add title column to questionnaire

Revision ID: 9626a4485615
Revises: 1bfda0b4d438
Create Date: 2021-01-10 14:11:45.076415

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9626a4485615'
down_revision = '1bfda0b4d438'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("questionnaire") as bop:
        bop.add_column(
            sa.Column(
                "title",
                sa.Unicode(256),
                nullable=True,
            )
        )
    op.execute(
        "UPDATE questionnaire SET title = 'Unbenannt' WHERE title IS NULL"
    )

    with op.batch_alter_table("questionnaire") as bop:
        bop.alter_column(
            "title",
            nullable=False,
        )


def downgrade():
    with op.batch_alter_table("questionnaire") as bop:
        bop.drop_column("title")
