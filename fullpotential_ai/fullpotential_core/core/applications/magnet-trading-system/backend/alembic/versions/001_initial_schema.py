"""Initial schema

Revision ID: 001
Revises: 
Create Date: 2025-11-19 23:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Positions table
    op.create_table(
        'positions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('symbol', sa.String(20), nullable=False),
        sa.Column('direction', sa.String(10), nullable=False),
        sa.Column('size_usd', sa.Numeric(12, 2), nullable=False),
        sa.Column('leverage', sa.Numeric(4, 2), nullable=False),
        sa.Column('entry_price', sa.Numeric(15, 8), nullable=False),
        sa.Column('stop_price', sa.Numeric(15, 8)),
        sa.Column('target_price', sa.Numeric(15, 8)),
        sa.Column('magnet_tier', sa.Integer()),
        sa.Column('opened_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('closed_at', sa.DateTime()),
        sa.Column('pnl', sa.Numeric(12, 2)),
        sa.Column('pnl_percent', sa.Numeric(8, 4)),
        sa.Column('closure_reason', sa.String(50)),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_positions_symbol', 'positions', ['symbol'])
    op.create_index('idx_positions_opened', 'positions', ['opened_at'])

    # Account snapshots
    op.create_table(
        'account_snapshots',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('equity', sa.Numeric(12, 2), nullable=False),
        sa.Column('available_margin', sa.Numeric(12, 2), nullable=False),
        sa.Column('open_positions_value', sa.Numeric(12, 2), nullable=False),
        sa.Column('unrealized_pnl', sa.Numeric(12, 2), nullable=False),
        sa.Column('daily_pnl', sa.Numeric(12, 2), nullable=False),
        sa.Column('leverage_used', sa.Numeric(4, 2), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_snapshots_timestamp', 'account_snapshots', ['timestamp'], postgresql_using='btree')

    # Magnet detections
    op.create_table(
        'magnet_detections',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('level', sa.Numeric(15, 8), nullable=False),
        sa.Column('magnet_type', sa.String(20), nullable=False),
        sa.Column('strength', sa.Numeric(5, 2), nullable=False),
        sa.Column('conflict', sa.Numeric(5, 2), nullable=False),
        sa.Column('distance_atr', sa.Numeric(5, 2), nullable=False),
        sa.Column('volatility_pressure', sa.Numeric(5, 2), nullable=False),
        sa.Column('tier', sa.Integer(), nullable=False),
        sa.Column('timeframe', sa.String(10), nullable=False),
        sa.Column('detected_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_magnets_detected', 'magnet_detections', ['detected_at'])
    op.create_index('idx_magnets_tier', 'magnet_detections', ['tier'])

    # Fuse events
    op.create_table(
        'fuse_events',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('trigger_type', sa.String(30), nullable=False),
        sa.Column('severity', sa.String(20), nullable=False),
        sa.Column('daily_loss_percent', sa.Numeric(5, 2)),
        sa.Column('action_taken', sa.String(100)),
        sa.Column('timestamp', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_fuse_timestamp', 'fuse_events', ['timestamp'])

    # Investors
    op.create_table(
        'investors',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(255), nullable=False, unique=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('share_percent', sa.Numeric(5, 4), nullable=False),
        sa.Column('initial_investment', sa.Numeric(12, 2), nullable=False),
        sa.Column('investment_date', sa.Date(), nullable=False),
        sa.Column('kyc_verified', sa.Boolean(), default=False),
        sa.Column('status', sa.String(20), default='active'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )

    # Investor snapshots
    op.create_table(
        'investor_snapshots',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('investor_id', sa.Integer(), nullable=False),
        sa.Column('equity_value', sa.Numeric(12, 2), nullable=False),
        sa.Column('total_return', sa.Numeric(12, 2), nullable=False),
        sa.Column('return_percent', sa.Numeric(8, 4), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['investor_id'], ['investors.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_investor_snapshots', 'investor_snapshots', ['investor_id', 'timestamp'])

    # System config
    op.create_table(
        'system_config',
        sa.Column('key', sa.String(100), nullable=False),
        sa.Column('value', sa.Text(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('key')
    )

    # Idempotency keys
    op.create_table(
        'idempotency_keys',
        sa.Column('key', sa.String(255), nullable=False),
        sa.Column('response_data', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('key')
    )
    op.create_index('idx_idempotency_expires', 'idempotency_keys', ['expires_at'])

    # Initial config values
    op.execute("""
        INSERT INTO system_config (key, value) VALUES
        ('initial_equity', '430000.00'),
        ('trading_mode', 'paper_trade'),
        ('fuse_armed', 'true'),
        ('max_leverage', '3.0')
    """)


def downgrade() -> None:
    op.drop_table('idempotency_keys')
    op.drop_table('system_config')
    op.drop_table('investor_snapshots')
    op.drop_table('investors')
    op.drop_table('fuse_events')
    op.drop_table('magnet_detections')
    op.drop_table('account_snapshots')
    op.drop_table('positions')
