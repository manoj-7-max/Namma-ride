import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("phone", sa.String(13), nullable=False),
        sa.Column("display_name", sa.String(100), nullable=False),
        sa.Column("role", sa.String(10), nullable=False),
        sa.Column(
            "driver_approved", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column("vehicle_number", sa.String(20), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint("role IN ('customer', 'driver')", name="valid_user_role"),
        sa.UniqueConstraint("phone"),
    )
    op.create_index("ix_users_phone", "users", ["phone"], unique=True)
    op.create_index("ix_users_role", "users", ["role"])
    op.create_table(
        "otp_challenges",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("phone", sa.String(13), nullable=False),
        sa.Column("role", sa.String(10), nullable=False),
        sa.Column("display_name", sa.String(100), nullable=True),
        sa.Column("vehicle_number", sa.String(20), nullable=True),
        sa.Column("code_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("consumed_at", sa.DateTime(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_otp_challenges_phone", "otp_challenges", ["phone"])
    op.create_table(
        "rides",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "customer_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False
        ),
        sa.Column("driver_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("pickup", sa.String(200), nullable=False),
        sa.Column("dropoff", sa.String(200), nullable=False),
        sa.Column("distance_tenths_km", sa.Integer(), nullable=False),
        sa.Column("estimated_fare_paise", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(12), nullable=False, server_default="requested"),
        sa.Column("cancellation_reason", sa.String(200), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False
        ),
        sa.CheckConstraint(
            "status IN ('requested','accepted','arrived','started','completed','cancelled')",
            name="valid_ride_status",
        ),
        sa.CheckConstraint("estimated_fare_paise >= 0", name="nonnegative_fare"),
        sa.CheckConstraint("distance_tenths_km > 0", name="positive_distance"),
    )
    op.create_index("ix_rides_customer_id", "rides", ["customer_id"])
    op.create_index("ix_rides_driver_id", "rides", ["driver_id"])
    op.create_index("ix_rides_status", "rides", ["status"])
    op.create_table(
        "ride_rejections",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "ride_id",
            sa.Integer(),
            sa.ForeignKey("rides.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "driver_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("ride_id", "driver_id", name="uq_ride_driver_rejection"),
    )


def downgrade():
    op.drop_table("ride_rejections")
    op.drop_index("ix_rides_status", table_name="rides")
    op.drop_index("ix_rides_driver_id", table_name="rides")
    op.drop_index("ix_rides_customer_id", table_name="rides")
    op.drop_table("rides")
    op.drop_index("ix_otp_challenges_phone", table_name="otp_challenges")
    op.drop_table("otp_challenges")
    op.drop_index("ix_users_role", table_name="users")
    op.drop_index("ix_users_phone", table_name="users")
    op.drop_table("users")
