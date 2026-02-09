-- Feature Flagging System - Enhanced Supabase Schema v2
-- Adds: API Keys, Audit Logs, Scheduling, Targeting Rules
-- Run this AFTER the original schema

-- ============================================================================
-- API KEYS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS api_keys (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    key_hash VARCHAR(64) NOT NULL UNIQUE,  -- SHA-256 hash of the key
    key_prefix VARCHAR(8) NOT NULL,         -- First 8 chars for identification
    name VARCHAR(255) NOT NULL,
    description TEXT,
    client_id VARCHAR(255) REFERENCES clients(client_id) ON DELETE CASCADE,
    permissions JSONB DEFAULT '["read"]'::jsonb,  -- ["read", "write", "admin"]
    rate_limit INTEGER DEFAULT 1000,        -- Requests per hour
    is_active BOOLEAN DEFAULT TRUE,
    expires_at TIMESTAMP WITH TIME ZONE,
    last_used_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by VARCHAR(255),
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX idx_api_keys_hash ON api_keys(key_hash);
CREATE INDEX idx_api_keys_client ON api_keys(client_id);
CREATE INDEX idx_api_keys_active ON api_keys(is_active) WHERE is_active = TRUE;

-- ============================================================================
-- RATE LIMITING TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS rate_limit_buckets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    key_id UUID REFERENCES api_keys(id) ON DELETE CASCADE,
    window_start TIMESTAMP WITH TIME ZONE NOT NULL,
    request_count INTEGER DEFAULT 1,
    UNIQUE(key_id, window_start)
);

CREATE INDEX idx_rate_limit_key ON rate_limit_buckets(key_id);
CREATE INDEX idx_rate_limit_window ON rate_limit_buckets(window_start);

-- ============================================================================
-- AUDIT LOGS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    action VARCHAR(100) NOT NULL,           -- 'create', 'update', 'delete', 'enable', 'disable', etc.
    entity_type VARCHAR(100) NOT NULL,      -- 'feature', 'client', 'ruleset', 'api_key', etc.
    entity_id VARCHAR(255),
    entity_name VARCHAR(255),
    actor_type VARCHAR(50) NOT NULL,        -- 'user', 'api_key', 'system'
    actor_id VARCHAR(255),
    actor_name VARCHAR(255),
    changes JSONB,                          -- {"before": {...}, "after": {...}}
    metadata JSONB DEFAULT '{}'::jsonb,
    ip_address INET,
    user_agent TEXT
);

CREATE INDEX idx_audit_logs_timestamp ON audit_logs(timestamp DESC);
CREATE INDEX idx_audit_logs_action ON audit_logs(action);
CREATE INDEX idx_audit_logs_entity ON audit_logs(entity_type, entity_id);
CREATE INDEX idx_audit_logs_actor ON audit_logs(actor_type, actor_id);

-- ============================================================================
-- FEATURE SCHEDULES TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS feature_schedules (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    feature_name VARCHAR(255) NOT NULL,
    ruleset_name VARCHAR(255),              -- NULL means applies to all rulesets
    client_id VARCHAR(255),                 -- NULL means applies to all clients
    schedule_type VARCHAR(50) NOT NULL,     -- 'one_time', 'recurring', 'date_range'
    start_at TIMESTAMP WITH TIME ZONE,
    end_at TIMESTAMP WITH TIME ZONE,
    timezone VARCHAR(50) DEFAULT 'UTC',
    cron_expression VARCHAR(100),           -- For recurring: "0 9 * * 1-5" (weekdays 9am)
    is_active BOOLEAN DEFAULT TRUE,
    enabled_during_schedule BOOLEAN DEFAULT TRUE,  -- Enable or disable during schedule
    priority INTEGER DEFAULT 0,             -- Higher priority wins on conflicts
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by VARCHAR(255),
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX idx_schedules_feature ON feature_schedules(feature_name);
CREATE INDEX idx_schedules_active ON feature_schedules(is_active) WHERE is_active = TRUE;
CREATE INDEX idx_schedules_times ON feature_schedules(start_at, end_at);

-- ============================================================================
-- TARGETING RULES TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS targeting_rules (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    feature_name VARCHAR(255) NOT NULL,
    ruleset_name VARCHAR(255),              -- NULL means applies to all rulesets
    priority INTEGER DEFAULT 0,             -- Higher priority evaluated first
    conditions JSONB NOT NULL,              -- Array of conditions with AND/OR logic
    -- Example conditions:
    -- [
    --   {"attribute": "country", "operator": "in", "values": ["US", "CA"]},
    --   {"attribute": "device", "operator": "equals", "value": "mobile"},
    --   {"attribute": "user_id", "operator": "percentage", "value": 50}
    -- ]
    action VARCHAR(50) NOT NULL DEFAULT 'enable',  -- 'enable', 'disable', 'variant'
    variant_value JSONB,                    -- For A/B tests or variants
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by VARCHAR(255),
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX idx_targeting_feature ON targeting_rules(feature_name);
CREATE INDEX idx_targeting_active ON targeting_rules(is_active) WHERE is_active = TRUE;
CREATE INDEX idx_targeting_priority ON targeting_rules(priority DESC);

-- ============================================================================
-- FEATURE FLAG OVERRIDES TABLE (per-client or per-user overrides)
-- ============================================================================
CREATE TABLE IF NOT EXISTS feature_overrides (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    feature_name VARCHAR(255) NOT NULL,
    override_type VARCHAR(50) NOT NULL,     -- 'client', 'user', 'segment'
    override_id VARCHAR(255) NOT NULL,      -- client_id, user_id, or segment_id
    is_enabled BOOLEAN NOT NULL,
    variant_value JSONB,
    reason TEXT,
    expires_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by VARCHAR(255),
    UNIQUE(feature_name, override_type, override_id)
);

CREATE INDEX idx_overrides_feature ON feature_overrides(feature_name);
CREATE INDEX idx_overrides_lookup ON feature_overrides(override_type, override_id);

-- ============================================================================
-- USER SEGMENTS TABLE (for targeting)
-- ============================================================================
CREATE TABLE IF NOT EXISTS user_segments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    rules JSONB NOT NULL,                   -- Conditions to match users
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by VARCHAR(255),
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX idx_segments_active ON user_segments(is_active) WHERE is_active = TRUE;

-- ============================================================================
-- FEATURE FLAG METRICS TABLE
-- ============================================================================
CREATE TABLE IF NOT EXISTS feature_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    feature_name VARCHAR(255) NOT NULL,
    client_id VARCHAR(255),
    date DATE NOT NULL DEFAULT CURRENT_DATE,
    evaluations_total INTEGER DEFAULT 0,
    evaluations_enabled INTEGER DEFAULT 0,
    evaluations_disabled INTEGER DEFAULT 0,
    unique_users INTEGER DEFAULT 0,
    metadata JSONB DEFAULT '{}'::jsonb,
    UNIQUE(feature_name, client_id, date)
);

CREATE INDEX idx_metrics_feature ON feature_metrics(feature_name);
CREATE INDEX idx_metrics_date ON feature_metrics(date DESC);
CREATE INDEX idx_metrics_client ON feature_metrics(client_id);

-- ============================================================================
-- UPDATE TRIGGERS
-- ============================================================================
CREATE TRIGGER update_schedules_updated_at BEFORE UPDATE ON feature_schedules
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_targeting_updated_at BEFORE UPDATE ON targeting_rules
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_segments_updated_at BEFORE UPDATE ON user_segments
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- ROW LEVEL SECURITY
-- ============================================================================
ALTER TABLE api_keys ENABLE ROW LEVEL SECURITY;
ALTER TABLE rate_limit_buckets ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE feature_schedules ENABLE ROW LEVEL SECURITY;
ALTER TABLE targeting_rules ENABLE ROW LEVEL SECURITY;
ALTER TABLE feature_overrides ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_segments ENABLE ROW LEVEL SECURITY;
ALTER TABLE feature_metrics ENABLE ROW LEVEL SECURITY;

-- Policies for authenticated users
CREATE POLICY "Allow all for authenticated users" ON api_keys FOR ALL USING (auth.role() = 'authenticated');
CREATE POLICY "Allow all for authenticated users" ON rate_limit_buckets FOR ALL USING (auth.role() = 'authenticated');
CREATE POLICY "Allow all for authenticated users" ON audit_logs FOR ALL USING (auth.role() = 'authenticated');
CREATE POLICY "Allow all for authenticated users" ON feature_schedules FOR ALL USING (auth.role() = 'authenticated');
CREATE POLICY "Allow all for authenticated users" ON targeting_rules FOR ALL USING (auth.role() = 'authenticated');
CREATE POLICY "Allow all for authenticated users" ON feature_overrides FOR ALL USING (auth.role() = 'authenticated');
CREATE POLICY "Allow all for authenticated users" ON user_segments FOR ALL USING (auth.role() = 'authenticated');
CREATE POLICY "Allow all for authenticated users" ON feature_metrics FOR ALL USING (auth.role() = 'authenticated');

-- Read policies for anon (service role for API)
CREATE POLICY "Allow read for anon" ON audit_logs FOR SELECT USING (true);
CREATE POLICY "Allow read for anon" ON feature_schedules FOR SELECT USING (true);
CREATE POLICY "Allow read for anon" ON targeting_rules FOR SELECT USING (true);
CREATE POLICY "Allow read for anon" ON feature_overrides FOR SELECT USING (true);
CREATE POLICY "Allow read for anon" ON user_segments FOR SELECT USING (true);
CREATE POLICY "Allow read for anon" ON feature_metrics FOR SELECT USING (true);

-- ============================================================================
-- HELPER FUNCTIONS
-- ============================================================================

-- Function to clean up old rate limit buckets
CREATE OR REPLACE FUNCTION cleanup_old_rate_limits()
RETURNS void AS $$
BEGIN
    DELETE FROM rate_limit_buckets
    WHERE window_start < NOW() - INTERVAL '2 hours';
END;
$$ LANGUAGE plpgsql;

-- Function to increment feature metrics
CREATE OR REPLACE FUNCTION increment_feature_metric(
    p_feature_name VARCHAR(255),
    p_client_id VARCHAR(255),
    p_enabled BOOLEAN
)
RETURNS void AS $$
BEGIN
    INSERT INTO feature_metrics (feature_name, client_id, date, evaluations_total, evaluations_enabled, evaluations_disabled)
    VALUES (p_feature_name, p_client_id, CURRENT_DATE, 1,
            CASE WHEN p_enabled THEN 1 ELSE 0 END,
            CASE WHEN p_enabled THEN 0 ELSE 1 END)
    ON CONFLICT (feature_name, client_id, date)
    DO UPDATE SET
        evaluations_total = feature_metrics.evaluations_total + 1,
        evaluations_enabled = feature_metrics.evaluations_enabled + CASE WHEN p_enabled THEN 1 ELSE 0 END,
        evaluations_disabled = feature_metrics.evaluations_disabled + CASE WHEN p_enabled THEN 0 ELSE 1 END;
END;
$$ LANGUAGE plpgsql;
