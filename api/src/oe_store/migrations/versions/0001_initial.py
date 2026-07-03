"""Initial schema: users, graphs, memberships, share links, nodes, icp refs,
flywheels, flywheel nodes/edges.

Revision ID: 0001
Revises:
"""
from alembic import op

from oe_store.models import Base

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # First revision: create everything from the ORM metadata. Later schema
    # changes must be written as explicit alembic operations.
    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind())
