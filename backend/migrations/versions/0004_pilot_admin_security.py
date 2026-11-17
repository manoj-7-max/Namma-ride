import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade():
    op.create_index("ix_ride_dispatches_driver_id", "ride_dispatches", ["driver_id"])
    op.create_index("ix_ride_dispatches_status", "ride_dispatches", ["status"])
    op.create_index("ix_ride_dispatches_expires_at", "ride_dispatches", ["expires_at"])
    op.add_column(
        "users",
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.add_column(
        "users",
        sa.Column(
            "driver_suspended", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
    )
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("actor_role", sa.String(20), nullable=False),
        sa.Column("action", sa.String(60), nullable=False),
        sa.Column("target_type", sa.String(30), nullable=False),
        sa.Column("target_id", sa.Integer(), nullable=True),
        sa.Column("detail", sa.String(200), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])


def downgrade():
    op.drop_index("ix_audit_logs_created_at", table_name="audit_logs")
    op.drop_index("ix_audit_logs_action", table_name="audit_logs")
    op.drop_table("audit_logs")
    op.drop_column("users", "driver_suspended")
    op.drop_column("users", "is_active")
    op.drop_index("ix_ride_dispatches_expires_at", table_name="ride_dispatches")
    op.drop_index("ix_ride_dispatches_status", table_name="ride_dispatches")
    op.drop_index("ix_ride_dispatches_driver_id", table_name="ride_dispatches")
