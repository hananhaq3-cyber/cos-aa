"""008 — Add goal column to sessions table."""
from alembic import op
import sqlalchemy as sa

revision = "008"
down_revision = "007"


def upgrade() -> None:
    op.add_column(
        "sessions",
        sa.Column("goal", sa.Text, nullable=True),
    )


def downgrade() -> None:
    op.drop_column("sessions", "goal")
