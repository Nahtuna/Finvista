"""add SMC features table

Revision ID: add_smc_features
Revises: 9d9fdc715c30
Create Date: 2024-08-04 12:15:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision = 'add_smc_features'
down_revision = '9d9fdc715c30'
branch_labels = None
depends_on = None


def upgrade():
    # Create SMC features table (using Text for JSON storage in SQLite)
    op.create_table(
        'smc_features',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('symbol', sa.String(), nullable=False),
        sa.Column('date', sa.String(), nullable=False),
        sa.Column('pivot_highs', sa.Text(), nullable=True),
        sa.Column('pivot_lows', sa.Text(), nullable=True),
        sa.Column('bsl_sweeps', sa.Text(), nullable=True),
        sa.Column('ssl_sweeps', sa.Text(), nullable=True),
        sa.Column('choch_bullish', sa.Text(), nullable=True),
        sa.Column('choch_bearish', sa.Text(), nullable=True),
        sa.Column('bos_bullish', sa.Text(), nullable=True),
        sa.Column('bos_bearish', sa.Text(), nullable=True),
        sa.Column('fvg', sa.Text(), nullable=True),
        sa.Column('order_blocks', sa.Text(), nullable=True),
        sa.Column('wyckoff_events', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    op.create_index('ix_smc_features_symbol', 'smc_features', ['symbol'])
    op.create_index('ix_smc_features_date', 'smc_features', ['date'])
    op.create_index('ix_smc_features_symbol_date', 'smc_features', ['symbol', 'date'])


def downgrade():
    # Drop indexes
    op.drop_index('ix_smc_features_symbol_date', table_name='smc_features')
    op.drop_index('ix_smc_features_date', table_name='smc_features')
    op.drop_index('ix_smc_features_symbol', table_name='smc_features')
    
    # Drop table
    op.drop_table('smc_features')
