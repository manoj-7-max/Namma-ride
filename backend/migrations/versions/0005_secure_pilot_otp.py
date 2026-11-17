import sqlalchemy as sa
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "pilot_otp_recipients",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("phone", sa.String(13), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint("phone"),
    )
    op.create_index(
        "ix_pilot_otp_recipients_phone",
        "pilot_otp_recipients",
        ["phone"],
        unique=True,
    )
    op.create_table(
        "pilot_otp_deliveries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "challenge_id",
            sa.Integer(),
            sa.ForeignKey("otp_challenges.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("encrypted_code", sa.String(255), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("retrieved_at", sa.DateTime(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint("challenge_id"),
    )
    op.create_index(
        "ix_pilot_otp_deliveries_challenge_id",
        "pilot_otp_deliveries",
        ["challenge_id"],
        unique=True,
    )
    op.create_index(
        "ix_pilot_otp_deliveries_expires_at",
        "pilot_otp_deliveries",
        ["expires_at"],
    )


def downgrade():
    op.drop_index(
        "ix_pilot_otp_deliveries_expires_at", table_name="pilot_otp_deliveries"
    )
    op.drop_index(
        "ix_pilot_otp_deliveries_challenge_id", table_name="pilot_otp_deliveries"
    )
    op.drop_table("pilot_otp_deliveries")
    op.drop_index("ix_pilot_otp_recipients_phone", table_name="pilot_otp_recipients")
    op.drop_table("pilot_otp_recipients")
