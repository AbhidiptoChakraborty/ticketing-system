"""Add tickets table

Revision ID: 002
Revises: 001
Create Date: 2026-06-07 00:00:00.000001

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'tickets',
        sa.Column(
            'id',
            sa.Integer(),
            primary_key=True,
            nullable=False,
        ),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column(
            'status',
            sa.String(),
            nullable=False,
            server_default='OPEN',
        ),
        sa.Column('response', sa.Text(), nullable=True),
        sa.Column(
            'owner_id',
            sa.Integer(),
            sa.ForeignKey('users.id'),
            nullable=False,
        ),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        op.f('ix_tickets_id'),
        'tickets',
        ['id'],
        unique=False,
    )
    op.create_index(
        op.f('ix_tickets_owner_id'),
        'tickets',
        ['owner_id'],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f('ix_tickets_owner_id'), table_name='tickets')
    op.drop_index(op.f('ix_tickets_id'), table_name='tickets')
    op.drop_table('tickets')
