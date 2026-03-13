"""004 — CoT audit log and session messages."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "004"
down_revision = "003"


def upgrade() -> None:
    op.create_table(
        "cot_audit_log",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID, nullable=False),
        sa.Column("session_id", UUID, nullable=False),
        sa.Column("trace_id", UUID, nullable=False),
        sa.Column("cycle_number", sa.Integer, nullable=False),
        sa.Column("cot_chain", JSONB, nullable=False),
        sa.Column("situation_summary", sa.Text, nullable=True),
        sa.Column("recommended_option", sa.Text, nullable=True),
        sa.Column("confidence", sa.Float, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )
    op.create_index("idx_cot_trace", "cot_audit_log", ["trace_id"])
    op.execute("ALTER TABLE cot_audit_log ENABLE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY rls_cot ON cot_audit_log "
        "USING (tenant_id = current_setting('app.tenant_id')::UUID)"
    )

    op.create_table(
        "session_messages",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID, nullable=False),
        sa.Column("session_id", UUID, sa.ForeignKey("sessions.id"), nullable=False),
        sa.Column("role", sa.String(32), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("cot_chain", JSONB, nullable=True),
        sa.Column("trace_id", UUID, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )
    op.execute("ALTER TABLE session_messages ENABLE ROW LEVEL SECURITY")
    op.execute(
        "CREATE POLICY rls_messages ON session_messages "
        "USING (tenant_id = current_setting('app.tenant_id')::UUID)"
    )


def downgrade() -> None:
    op.drop_table("session_messages")
    op.drop_table("cot_audit_log")
