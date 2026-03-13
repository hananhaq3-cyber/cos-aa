"""002 — Episodic and procedural memory tables."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY

revision = "002"
down_revision = "001"


def upgrade() -> None:
    op.create_table(
        "episodic_memories",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID, nullable=False),
        sa.Column("user_id", UUID, nullable=True),
        sa.Column("agent_id", UUID, nullable=False),
        sa.Column("session_id", UUID, nullable=False),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("content", JSONB, nullable=False),
        sa.Column("embedding_id", sa.String(256), nullable=True),
        sa.Column("importance_score", sa.Float, server_default="0.5"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("accessed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("access_count", sa.Integer, server_default="0"),
        sa.Column("tags", ARRAY(sa.Text), nullable=True),
    )
    op.create_index("idx_episodic_tenant_session", "episodic_memories", ["tenant_id", "session_id"])
    op.execute("CREATE INDEX idx_episodic_tags ON episodic_memories USING GIN(tags)")
    op.execute("ALTER TABLE episodic_memories ENABLE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY rls_episodic ON episodic_memories "
        "USING (tenant_id = current_setting('app.tenant_id')::UUID)"
    )

    op.create_table(
        "procedural_patterns",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID, nullable=False),
        sa.Column("pattern_name", sa.String(256), nullable=False),
        sa.Column("task_type", sa.String(128), nullable=True),
        sa.Column("trigger_conditions", JSONB, nullable=True),
        sa.Column("action_sequence", JSONB, nullable=True),
        sa.Column("success_count", sa.Integer, server_default="0"),
        sa.Column("failure_count", sa.Integer, server_default="0"),
        sa.Column("avg_completion_time_ms", sa.Float, nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.UniqueConstraint("tenant_id", "pattern_name"),
    )
    op.execute("ALTER TABLE procedural_patterns ENABLE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY rls_procedural ON procedural_patterns "
        "USING (tenant_id = current_setting('app.tenant_id')::UUID)"
    )


def downgrade() -> None:
    op.drop_table("procedural_patterns")
    op.drop_table("episodic_memories")
