"""Add node_job_refs: outcomes and opportunities reference job nodes
(many-to-many), mirroring node_icp_refs.

Revision ID: 0002
Revises: 0001
"""
import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Fresh installs already get the table from 0001, which creates the whole
    # ORM metadata; this revision only upgrades databases created before jobs.
    if sa.inspect(op.get_bind()).has_table("node_job_refs"):
        return
    op.create_table(
        "node_job_refs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("node_id", sa.Uuid(), sa.ForeignKey("nodes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("job_node_id", sa.Uuid(), sa.ForeignKey("nodes.id", ondelete="CASCADE"), nullable=False),
        sa.UniqueConstraint("node_id", "job_node_id"),
    )


def downgrade() -> None:
    op.drop_table("node_job_refs")
