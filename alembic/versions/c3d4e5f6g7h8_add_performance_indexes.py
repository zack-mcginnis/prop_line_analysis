"""add_performance_indexes

Revision ID: c3d4e5f6g7h8
Revises: b2c3d4e5f6g7
Create Date: 2026-01-03 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3d4e5f6g7h8'
down_revision: Union[str, None] = 'b2c3d4e5f6g7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add composite index for dashboard queries
    # This index optimizes the common query pattern: filter by game_commence_time and snapshot_time
    op.create_index(
        'idx_dashboard_query',
        'prop_line_snapshots',
        ['game_commence_time', 'snapshot_time', 'prop_type'],
        unique=False
    )
    
    # Add index for prop_type + snapshot_time (helps with filtered queries)
    op.create_index(
        'idx_prop_type_snapshot',
        'prop_line_snapshots',
        ['prop_type', 'snapshot_time'],
        unique=False
    )


def downgrade() -> None:
    # Remove the performance indexes
    op.drop_index('idx_prop_type_snapshot', table_name='prop_line_snapshots')
    op.drop_index('idx_dashboard_query', table_name='prop_line_snapshots')

