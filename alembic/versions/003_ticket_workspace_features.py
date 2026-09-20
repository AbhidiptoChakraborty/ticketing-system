"""Add ticket triage fields and conversation thread.

Revision ID: 003
Revises: 002
Create Date: 2026-09-20 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "tickets",
        sa.Column(
            "priority",
            sa.String(),
            nullable=False,
            server_default="MEDIUM",
        ),
    )
    op.add_column(
        "tickets",
        sa.Column(
            "category",
            sa.String(),
            nullable=False,
            server_default="GENERAL",
        ),
    )
    op.create_index("ix_tickets_priority", "tickets", ["priority"])
    op.create_index("ix_tickets_category", "tickets", ["category"])
    op.create_table(
        "ticket_comments",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column(
            "ticket_id",
            sa.Integer(),
            sa.ForeignKey("tickets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "author_id",
            sa.Integer(),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_ticket_comments_id", "ticket_comments", ["id"])
    op.create_index(
        "ix_ticket_comments_ticket_id",
        "ticket_comments",
        ["ticket_id"],
    )
    op.create_index(
        "ix_ticket_comments_author_id",
        "ticket_comments",
        ["author_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_ticket_comments_author_id", table_name="ticket_comments")
    op.drop_index("ix_ticket_comments_ticket_id", table_name="ticket_comments")
    op.drop_index("ix_ticket_comments_id", table_name="ticket_comments")
    op.drop_table("ticket_comments")
    op.drop_index("ix_tickets_category", table_name="tickets")
    op.drop_index("ix_tickets_priority", table_name="tickets")
    op.drop_column("tickets", "category")
    op.drop_column("tickets", "priority")
