"""005 — Add OAuth columns to users table."""
from alembic import op
import sqlalchemy as sa

revision = "005"
down_revision = "004"


def upgrade() -> None:
    op.add_column("users", sa.Column("oauth_provider", sa.String(32), nullable=True))
    op.add_column("users", sa.Column("oauth_provider_id", sa.String(256), nullable=True))
    op.alter_column("users", "hashed_password", existing_type=sa.Text(), nullable=True)


def downgrade() -> None:
    op.alter_column("users", "hashed_password", existing_type=sa.Text(), nullable=False)
    op.drop_column("users", "oauth_provider_id")
    op.drop_column("users", "oauth_provider")
