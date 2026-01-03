"""add_sportsbook_timestamps

Revision ID: b2c3d4e5f6g7
Revises: a1b2c3d4e5f6
Create Date: 2026-01-03 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6g7'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add timestamp columns for each sportsbook
    op.add_column('prop_line_snapshots', sa.Column('consensus_timestamp', sa.DateTime(timezone=True), nullable=True))
    op.add_column('prop_line_snapshots', sa.Column('draftkings_timestamp', sa.DateTime(timezone=True), nullable=True))
    op.add_column('prop_line_snapshots', sa.Column('fanduel_timestamp', sa.DateTime(timezone=True), nullable=True))
    op.add_column('prop_line_snapshots', sa.Column('betmgm_timestamp', sa.DateTime(timezone=True), nullable=True))
    op.add_column('prop_line_snapshots', sa.Column('caesars_timestamp', sa.DateTime(timezone=True), nullable=True))
    op.add_column('prop_line_snapshots', sa.Column('pointsbet_timestamp', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    # Remove the timestamp columns
    op.drop_column('prop_line_snapshots', 'pointsbet_timestamp')
    op.drop_column('prop_line_snapshots', 'caesars_timestamp')
    op.drop_column('prop_line_snapshots', 'betmgm_timestamp')
    op.drop_column('prop_line_snapshots', 'fanduel_timestamp')
    op.drop_column('prop_line_snapshots', 'draftkings_timestamp')
    op.drop_column('prop_line_snapshots', 'consensus_timestamp')
