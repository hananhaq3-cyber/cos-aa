"""003 — Agent types, instances, and capability gap events."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY

revision = "003"
down_revision = "002"


def upgrade() -> None:
    op.create_table(
        "agent_types",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID, nullable=True),
        sa.Column("type_name", sa.String(256), nullable=False),
        sa.Column("definition", JSONB, nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="active"),
        sa.Column("image_tag", sa.String(512), nullable=True),
        sa.Column("k8s_deployment_name", sa.String(256), nullable=True),
        sa.Column("created_by", sa.String(32), server_default="SYSTEM_AUTO"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deprecated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("task_count_total", sa.BigInteger, server_default="0"),
        sa.Column("task_count_success", sa.BigInteger, server_default="0"),
        sa.UniqueConstraint("tenant_id", "type_name"),
    )

    op.create_table(
        "agent_instances",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID, nullable=True),
        sa.Column("type_id", UUID, sa.ForeignKey("agent_types.id"), nullable=False),
        sa.Column("instance_name", sa.String(256), nullable=True),
        sa.Column("status", sa.String(32), server_default="starting"),
        sa.Column("current_task_count", sa.Integer, server_default="0"),
        sa.Column("last_heartbeat_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
    )

    op.create_table(
        "agent_gap_events",
        sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID, nullable=False),
        sa.Column("task_type", sa.String(256), nullable=False),
        sa.Column("gap_frequency", sa.Integer, server_default="1"),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()")),
        sa.Column("sample_task_ids", ARRAY(UUID), nullable=True),
        sa.Column("status", sa.String(32), server_default="open"),
        sa.UniqueConstraint("tenant_id", "task_type"),
    )


def downgrade() -> None:
    op.drop_table("agent_gap_events")
    op.drop_table("agent_instances")
    op.drop_table("agent_types")
