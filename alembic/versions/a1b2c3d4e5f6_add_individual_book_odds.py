"""add_individual_book_odds

Revision ID: a1b2c3d4e5f6
Revises: 09d0389c0b53
Create Date: 2026-01-03 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '09d0389c0b53'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Rename existing odds columns to consensus_over_odds and consensus_under_odds
    op.alter_column('prop_line_snapshots', 'over_odds', new_column_name='consensus_over_odds')
    op.alter_column('prop_line_snapshots', 'under_odds', new_column_name='consensus_under_odds')
    
    # Add over/under odds columns for each sportsbook
    # DraftKings
    op.add_column('prop_line_snapshots', sa.Column('draftkings_over_odds', sa.Integer(), nullable=True))
    op.add_column('prop_line_snapshots', sa.Column('draftkings_under_odds', sa.Integer(), nullable=True))
    
    # FanDuel
    op.add_column('prop_line_snapshots', sa.Column('fanduel_over_odds', sa.Integer(), nullable=True))
    op.add_column('prop_line_snapshots', sa.Column('fanduel_under_odds', sa.Integer(), nullable=True))
    
    # BetMGM
    op.add_column('prop_line_snapshots', sa.Column('betmgm_over_odds', sa.Integer(), nullable=True))
    op.add_column('prop_line_snapshots', sa.Column('betmgm_under_odds', sa.Integer(), nullable=True))
    
    # Caesars
    op.add_column('prop_line_snapshots', sa.Column('caesars_over_odds', sa.Integer(), nullable=True))
    op.add_column('prop_line_snapshots', sa.Column('caesars_under_odds', sa.Integer(), nullable=True))
    
    # PointsBet
    op.add_column('prop_line_snapshots', sa.Column('pointsbet_over_odds', sa.Integer(), nullable=True))
    op.add_column('prop_line_snapshots', sa.Column('pointsbet_under_odds', sa.Integer(), nullable=True))


def downgrade() -> None:
    # Remove the individual sportsbook odds columns
    op.drop_column('prop_line_snapshots', 'pointsbet_under_odds')
    op.drop_column('prop_line_snapshots', 'pointsbet_over_odds')
    op.drop_column('prop_line_snapshots', 'caesars_under_odds')
    op.drop_column('prop_line_snapshots', 'caesars_over_odds')
    op.drop_column('prop_line_snapshots', 'betmgm_under_odds')
    op.drop_column('prop_line_snapshots', 'betmgm_over_odds')
    op.drop_column('prop_line_snapshots', 'fanduel_under_odds')
    op.drop_column('prop_line_snapshots', 'fanduel_over_odds')
    op.drop_column('prop_line_snapshots', 'draftkings_under_odds')
    op.drop_column('prop_line_snapshots', 'draftkings_over_odds')
    
    # Rename back to original column names
    op.alter_column('prop_line_snapshots', 'consensus_under_odds', new_column_name='under_odds')
    op.alter_column('prop_line_snapshots', 'consensus_over_odds', new_column_name='over_odds')

