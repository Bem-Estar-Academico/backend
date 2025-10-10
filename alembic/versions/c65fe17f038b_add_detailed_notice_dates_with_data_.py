"""Add detailed notice dates with data migration

Revision ID: c65fe17f038b
Revises: bac283692401
Create Date: 2025-10-02 11:56:48.633402

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "c65fe17f038b"
down_revision = "bac283692401"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "notices",
        sa.Column(
            "registration_start_date",
            sa.DateTime(),
            nullable=True,
            comment="Data de início das inscrições",
        ),
    )
    op.add_column(
        "notices",
        sa.Column(
            "registration_end_date",
            sa.DateTime(),
            nullable=True,
            comment="Data de término das inscrições",
        ),
    )
    op.add_column(
        "notices",
        sa.Column(
            "appeal_start_date",
            sa.DateTime(),
            nullable=True,
            comment="Data de início da fase de recursos",
        ),
    )
    op.add_column(
        "notices",
        sa.Column(
            "appeal_end_date",
            sa.DateTime(),
            nullable=True,
            comment="Data de término da fase de recursos",
        ),
    )
    op.add_column(
        "notices",
        sa.Column(
            "preliminary_result_date",
            sa.DateTime(),
            nullable=True,
            comment="Data de divulgação do resultado preliminar",
        ),
    )
    op.add_column(
        "notices",
        sa.Column(
            "final_result_date",
            sa.DateTime(),
            nullable=True,
            comment="Data de divulgação do resultado final",
        ),
    )

    op.execute(
        """
        UPDATE notices 
        SET 
            registration_start_date = start_date,
            registration_end_date = end_date
        WHERE start_date IS NOT NULL AND end_date IS NOT NULL
    """
    )

    op.alter_column("notices", "registration_start_date", nullable=False)
    op.alter_column("notices", "registration_end_date", nullable=False)

    op.drop_column("notices", "start_date")
    op.drop_column("notices", "end_date")


def downgrade() -> None:

    op.add_column("notices", sa.Column("start_date", sa.DateTime(), nullable=True))
    op.add_column("notices", sa.Column("end_date", sa.DateTime(), nullable=True))

    op.execute(
        """
        UPDATE notices 
        SET 
            start_date = registration_start_date,
            end_date = registration_end_date
        WHERE registration_start_date IS NOT NULL AND registration_end_date IS NOT NULL
    """
    )

    op.alter_column("notices", "start_date", nullable=False)
    op.alter_column("notices", "end_date", nullable=False)

    op.drop_column("notices", "final_result_date")
    op.drop_column("notices", "preliminary_result_date")
    op.drop_column("notices", "appeal_end_date")
    op.drop_column("notices", "appeal_start_date")
    op.drop_column("notices", "registration_end_date")
    op.drop_column("notices", "registration_start_date")
