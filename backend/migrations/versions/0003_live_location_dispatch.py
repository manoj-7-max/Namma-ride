import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_constraint("valid_ride_status", "rides", type_="check")
    op.create_check_constraint(
        "valid_ride_status",
        "rides",
        "status IN ('requested','matching','no_driver_available','accepted','arrived','started','completed','cancelled')",
    )
    for name in (
        "pickup_latitude",
        "pickup_longitude",
        "dropoff_latitude",
        "dropoff_longitude",
    ):
        op.add_column("rides", sa.Column(name, sa.Float(), nullable=True))
    op.create_table(
        "driver_locations",
        sa.Column(
            "driver_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("accuracy_m", sa.Float(), nullable=False),
        sa.Column("captured_at", sa.DateTime(), nullable=False),
        sa.Column("available", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_driver_locations_available", "driver_locations", ["available"])
    op.create_table(
        "ride_dispatches",
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
        sa.Column("status", sa.String(10), nullable=False, server_default="offered"),
        sa.Column("distance_m", sa.Integer(), nullable=False),
        sa.Column(
            "offered_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "status IN ('offered','rejected','expired','accepted')",
            name="valid_dispatch_status",
        ),
        sa.UniqueConstraint("ride_id", "driver_id", name="uq_dispatch_ride_driver"),
    )
    op.create_table(
        "ride_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "ride_id",
            sa.Integer(),
            sa.ForeignKey("rides.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("event_type", sa.String(40), nullable=False),
        sa.Column("detail", sa.String(200), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_ride_events_ride_id", "ride_events", ["ride_id"])


def downgrade():
    op.drop_index("ix_ride_events_ride_id", table_name="ride_events")
    op.drop_table("ride_events")
    op.drop_table("ride_dispatches")
    op.drop_index("ix_driver_locations_available", table_name="driver_locations")
    op.drop_table("driver_locations")
    for name in (
        "dropoff_longitude",
        "dropoff_latitude",
        "pickup_longitude",
        "pickup_latitude",
    ):
        op.drop_column("rides", name)
    op.drop_constraint("valid_ride_status", "rides", type_="check")
    op.create_check_constraint(
        "valid_ride_status",
        "rides",
        "status IN ('requested','accepted','arrived','started','completed','cancelled')",
    )
