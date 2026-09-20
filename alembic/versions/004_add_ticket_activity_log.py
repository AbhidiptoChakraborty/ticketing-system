"""Add the ticket activity log.

Revision ID: 004
Revises: 003
Create Date: 2026-09-20 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ticket_activities",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column(
            "ticket_id",
            sa.Integer(),
            sa.ForeignKey("tickets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "actor_id",
            sa.Integer(),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_ticket_activities_id", "ticket_activities", ["id"])
    op.create_index(
        "ix_ticket_activities_ticket_id",
        "ticket_activities",
        ["ticket_id"],
    )
    op.create_index(
        "ix_ticket_activities_actor_id",
        "ticket_activities",
        ["actor_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_ticket_activities_actor_id",
        table_name="ticket_activities",
    )
    op.drop_index(
        "ix_ticket_activities_ticket_id",
        table_name="ticket_activities",
    )
    op.drop_index("ix_ticket_activities_id", table_name="ticket_activities")
    op.drop_table("ticket_activities")
