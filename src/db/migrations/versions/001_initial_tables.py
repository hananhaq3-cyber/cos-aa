"""001 — Tenants, users, and sessions."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "001"
down_revision = None


def upgrade() -> None:
    op.create_table(
        "tenants",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(256), nullable=False, unique=True),
        sa.Column("plan", sa.String(64), server_default="shared"),
        sa.Column("require_agent_approval", sa.Boolean, server_default="true"),
        sa.Column("llm_api_key_encrypted", sa.Text, nullable=True),
        sa.Column(
            "quotas",
            JSONB,
            nullable=False,
            server_default='{"max_sessions_per_day":1000,"max_llm_tokens_per_day":5000000,"max_agents":20,"max_concurrent_tasks":50}',
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("is_active", sa.Boolean, server_default="true"),
    )

    op.create_table(
        "users",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID, sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("hashed_password", sa.Text, nullable=False),
        sa.Column("role", sa.String(32), nullable=False, server_default="end_user"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.UniqueConstraint("tenant_id", "email"),
    )
    op.execute("ALTER TABLE users ENABLE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY rls_users ON users USING (tenant_id = current_setting('app.tenant_id')::UUID)"
    )

    op.create_table(
        "sessions",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID, nullable=False),
        sa.Column("user_id", UUID, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("status", sa.String(32), server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("last_active_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )
    op.execute("ALTER TABLE sessions ENABLE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY rls_sessions ON sessions USING (tenant_id = current_setting('app.tenant_id')::UUID)"
    )


def downgrade() -> None:
    op.drop_table("sessions")
    op.drop_table("users")
    op.drop_table("tenants")
