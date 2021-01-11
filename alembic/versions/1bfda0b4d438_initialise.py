"""initialise

Revision ID: 1bfda0b4d438
Revises:
Create Date: 2021-01-10 13:49:21.003860

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '1bfda0b4d438'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "questionnaire",
        sa.Column(
            "id",
            sa.BINARY(8),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "edit_id",
            sa.BINARY(8),
            primary_key=True,
            nullable=False,
        )
    )

    op.create_table(
        "profile",
        sa.Column(
            "id",
            sa.Integer(),
            primary_key=True,
            nullable=False,
            autoincrement=True,
        ),
        sa.Column(
            "qid",
            sa.BINARY(8),
            sa.ForeignKey("questionnaire.id",
                          ondelete="CASCADE", onupdate="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "title",
            sa.Unicode(256),
            nullable=False,
        ),
        sa.Column(
            "description",
            sa.UnicodeText(),
            nullable=False,
        ),
    )

    op.create_table(
        "question",
        sa.Column(
            "id",
            sa.Integer(),
            primary_key=True,
            nullable=False,
            autoincrement=True,
        ),
        sa.Column(
            "qid",
            sa.BINARY(8),
            sa.ForeignKey("questionnaire.id",
                          ondelete="CASCADE", onupdate="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "order",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "title",
            sa.Unicode(256),
            nullable=False,
        ),
        sa.Column(
            "body",
            sa.UnicodeText(),
            nullable=True,
        ),
        sa.Column(
            "multiple_choice",
            sa.Boolean(),
            nullable=False,
        ),
        sa.Column(
            "shuffled",
            sa.Boolean(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "qid", "order",
            name="question_uix_qid_order",
        ),
    )

    op.create_table(
        "choice",
        sa.Column(
            "id",
            sa.Integer(),
            primary_key=True,
            nullable=False,
            autoincrement=True,
        ),
        sa.Column(
            "question_id",
            sa.Integer(),
            sa.ForeignKey("question.id",
                          ondelete="CASCADE", onupdate="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "order",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "body",
            sa.UnicodeText(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "question_id", "order",
            name="choice_uix_question_order",
        ),
    )

    op.create_table(
        "choice_profile_matrix",
        sa.Column(
            "choice_id",
            sa.Integer,
            sa.ForeignKey("choice.id",
                          ondelete="CASCADE", onupdate="CASCADE"),
            nullable=False,
            primary_key=True,
        ),
        sa.Column(
            "profile_id",
            sa.Integer,
            sa.ForeignKey("profile.id",
                          ondelete="CASCADE", onupdate="CASCADE"),
            nullable=False,
            primary_key=True,
        ),
        sa.Column(
            "weight",
            sa.Float(),
            nullable=False,
        ),
    )

    op.create_table(
        "participant",
        sa.Column(
            "id",
            sa.BINARY(8),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "qid",
            sa.BINARY(8),
            sa.ForeignKey("questionnaire.id",
                          ondelete="CASCADE", onupdate="CASCADE"),
            primary_key=True,
            nullable=False,
        ),
    )

    op.create_table(
        "answer",
        sa.Column(
            "participant_id",
            sa.BINARY(8),
            sa.ForeignKey("participant.id",
                          ondelete="CASCADE", onupdate="CASCADE"),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "choice_id",
            sa.Integer(),
            sa.ForeignKey("choice.id",
                          ondelete="CASCADE", onupdate="CASCADE"),
            primary_key=True,
            nullable=False,
        ),
    )


def downgrade():
    op.drop_table("answer")
    op.drop_table("participant")
    op.drop_table("choice_profile_matrix")
    op.drop_table("choice")
    op.drop_table("question")
    op.drop_table("profile")
    op.drop_table("questionnaire")
