"""remove_role_from_notice_teams

Revision ID: 02acccbeccbd
Revises: 290d2747e46f
Create Date: 2025-10-21 14:11:19.728215

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '02acccbeccbd'
down_revision = '290d2747e46f'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Remove a coluna role da tabela notice_teams
    op.drop_column('notice_teams', 'role')


def downgrade() -> None:
    # Adiciona a coluna de volta caso precise reverter
    op.add_column('notice_teams', 
                  sa.Column('role', sa.String(length=50), nullable=False, server_default='COORDINATOR'))
