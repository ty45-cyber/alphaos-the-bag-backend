-- creators: the asset universe
CREATE TABLE creators (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    bags_id VARCHAR(64) UNIQUE NOT NULL,
    wallet_address VARCHAR(64) NOT NULL,
    display_name VARCHAR(128) NOT NULL,
    token_mint VARCHAR(64) NOT NULL,
    narrative_score NUMERIC(6,2) DEFAULT 0.00,
    velocity_score NUMERIC(6,2) DEFAULT 0.00,
    whale_accumulation_score NUMERIC(6,2) DEFAULT 0.00,
    social_momentum_score NUMERIC(6,2) DEFAULT 0.00,
    market_cap_usd NUMERIC(20,2),
    volume_24h_usd NUMERIC(20,2),
    holder_count INTEGER DEFAULT 0,
    last_signal_computed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- signals: time-series momentum data
CREATE TABLE signals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    creator_id UUID NOT NULL REFERENCES creators(id) ON DELETE CASCADE,
    signal_type VARCHAR(32) NOT NULL,  -- 'whale_buy', 'narrative_spike', 'velocity_surge'
    strength NUMERIC(5,2) NOT NULL,    -- 0.00 to 100.00
    source VARCHAR(32) NOT NULL,       -- 'on_chain', 'social', 'bags_api'
    raw_metadata JSONB,
    computed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_signals_creator_computed ON signals(creator_id, computed_at DESC);
CREATE INDEX idx_signals_type_strength ON signals(signal_type, strength DESC);

-- users: alpha hunters
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    wallet_address VARCHAR(64) UNIQUE NOT NULL,
    username VARCHAR(64) UNIQUE,
    alpha_reputation_score NUMERIC(6,2) DEFAULT 0.00,
    total_pnl_usd NUMERIC(20,2) DEFAULT 0.00,
    win_rate NUMERIC(5,2) DEFAULT 0.00,
    is_public_portfolio BOOLEAN DEFAULT FALSE,
    streak_days INTEGER DEFAULT 0,
    alpha_tokens_staked NUMERIC(20,8) DEFAULT 0.00,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- portfolios: user allocations
CREATE TABLE portfolios (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(128) NOT NULL,
    total_value_usd NUMERIC(20,2) DEFAULT 0.00,
    last_rebalanced_at TIMESTAMPTZ,
    rebalance_strategy VARCHAR(32) DEFAULT 'ai_managed',  -- 'ai_managed', 'manual', 'copy_trade'
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- portfolio_allocations: positions within a portfolio
CREATE TABLE portfolio_allocations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    portfolio_id UUID NOT NULL REFERENCES portfolios(id) ON DELETE CASCADE,
    creator_id UUID NOT NULL REFERENCES creators(id),
    allocation_pct NUMERIC(5,2) NOT NULL,  -- 0.00 to 100.00
    entry_price_usd NUMERIC(20,8),
    current_price_usd NUMERIC(20,8),
    unrealized_pnl_usd NUMERIC(20,2) DEFAULT 0.00,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(portfolio_id, creator_id)
);

-- alpha_pools: aggregated staked capital
CREATE TABLE alpha_pools (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pool_name VARCHAR(128) NOT NULL,
    strategy_type VARCHAR(64) NOT NULL,  -- 'momentum', 'narrative', 'whale_follow'
    total_staked_usd NUMERIC(20,2) DEFAULT 0.00,
    apy_7d NUMERIC(6,2),
    apy_30d NUMERIC(6,2),
    performance_fee_pct NUMERIC(4,2) DEFAULT 2.00,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- pool_stakes: individual user stakes in pools
CREATE TABLE pool_stakes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pool_id UUID NOT NULL REFERENCES alpha_pools(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    staked_amount_usd NUMERIC(20,2) NOT NULL,
    share_pct NUMERIC(6,4),
    staked_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    unstaked_at TIMESTAMPTZ,
    UNIQUE(pool_id, user_id)
);

-- agent_decisions: audit trail for AI agent actions
CREATE TABLE agent_decisions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_name VARCHAR(64) NOT NULL,
    decision_type VARCHAR(64) NOT NULL,
    input_context JSONB NOT NULL,
    output_action JSONB NOT NULL,
    confidence_score NUMERIC(5,2),
    executed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);