-- Migration: Add nixo Feature Management System
-- Run this in your Supabase SQL editor or via migration tool
-- This creates tables for flexible ruleset management with inheritance

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- Feature Registry (synced from AVAILABLE_FEATURES)
-- ============================================================================
CREATE TABLE IF NOT EXISTS feature_registry (
    name VARCHAR(100) PRIMARY KEY,
    description TEXT,
    category VARCHAR(50) NOT NULL,
    is_enforced BOOLEAN DEFAULT FALSE,
    enforcement_locations JSONB DEFAULT '[]',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for category-based queries
CREATE INDEX IF NOT EXISTS idx_feature_registry_category ON feature_registry(category);

-- ============================================================================
-- Flexible Rulesets (unlimited, user-created)
-- ============================================================================
CREATE TABLE IF NOT EXISTS rulesets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) UNIQUE NOT NULL,
    display_name VARCHAR(200) NOT NULL,
    description TEXT,
    color VARCHAR(7) DEFAULT '#6366f1',  -- For UI badge color
    icon VARCHAR(50) DEFAULT 'package',   -- For UI icon
    inherits_from UUID REFERENCES rulesets(id) ON DELETE SET NULL,
    is_template BOOLEAN DEFAULT FALSE,    -- Mark as template for easy cloning
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by VARCHAR(100)
);

-- Index for inheritance queries
CREATE INDEX IF NOT EXISTS idx_rulesets_inherits_from ON rulesets(inherits_from);
CREATE INDEX IF NOT EXISTS idx_rulesets_is_template ON rulesets(is_template);

-- ============================================================================
-- Ruleset Feature Assignments
-- ============================================================================
CREATE TABLE IF NOT EXISTS ruleset_features (
    ruleset_id UUID REFERENCES rulesets(id) ON DELETE CASCADE,
    feature_name VARCHAR(100) REFERENCES feature_registry(name) ON DELETE CASCADE,
    enabled BOOLEAN DEFAULT TRUE,
    config JSONB DEFAULT '{}',  -- For future: percentage rollout, variants
    PRIMARY KEY (ruleset_id, feature_name)
);

-- Index for feature lookups
CREATE INDEX IF NOT EXISTS idx_ruleset_features_feature ON ruleset_features(feature_name);

-- ============================================================================
-- Client Ruleset Assignments
-- Note: Requires existing 'clients' table with 'id' column
-- ============================================================================
CREATE TABLE IF NOT EXISTS client_rulesets (
    client_id VARCHAR(255) PRIMARY KEY,
    ruleset_id UUID REFERENCES rulesets(id) ON DELETE SET NULL,
    assigned_at TIMESTAMPTZ DEFAULT NOW(),
    assigned_by VARCHAR(100),
    notes TEXT
);

-- Index for ruleset-based queries
CREATE INDEX IF NOT EXISTS idx_client_rulesets_ruleset ON client_rulesets(ruleset_id);

-- ============================================================================
-- Per-Client Feature Overrides (take precedence over ruleset)
-- ============================================================================
CREATE TABLE IF NOT EXISTS client_overrides (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id VARCHAR(255) NOT NULL,
    feature_name VARCHAR(100) REFERENCES feature_registry(name) ON DELETE CASCADE,
    enabled BOOLEAN NOT NULL,
    reason TEXT,
    expires_at TIMESTAMPTZ,  -- Optional expiration
    created_at TIMESTAMPTZ DEFAULT NOW(),
    created_by VARCHAR(100),
    UNIQUE(client_id, feature_name)
);

-- Indexes for override queries
CREATE INDEX IF NOT EXISTS idx_client_overrides_client ON client_overrides(client_id);
CREATE INDEX IF NOT EXISTS idx_client_overrides_feature ON client_overrides(feature_name);
CREATE INDEX IF NOT EXISTS idx_client_overrides_expires ON client_overrides(expires_at) WHERE expires_at IS NOT NULL;

-- ============================================================================
-- Audit Log for Changes
-- ============================================================================
CREATE TABLE IF NOT EXISTS feature_audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    action VARCHAR(50) NOT NULL,  -- create_ruleset, assign_client, add_override, etc.
    entity_type VARCHAR(50),      -- ruleset, client, override, feature
    entity_id VARCHAR(255),
    changes JSONB,                -- {before: {}, after: {}}
    actor VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for audit queries
CREATE INDEX IF NOT EXISTS idx_feature_audit_log_entity ON feature_audit_log(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_feature_audit_log_action ON feature_audit_log(action);
CREATE INDEX IF NOT EXISTS idx_feature_audit_log_created ON feature_audit_log(created_at DESC);

-- ============================================================================
-- Updated At Trigger Function
-- ============================================================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply triggers
DROP TRIGGER IF EXISTS update_feature_registry_updated_at ON feature_registry;
CREATE TRIGGER update_feature_registry_updated_at
    BEFORE UPDATE ON feature_registry
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_rulesets_updated_at ON rulesets;
CREATE TRIGGER update_rulesets_updated_at
    BEFORE UPDATE ON rulesets
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- Helper Views
-- ============================================================================

-- View: Rulesets with feature counts and client counts
CREATE OR REPLACE VIEW ruleset_summary AS
SELECT
    r.id,
    r.name,
    r.display_name,
    r.description,
    r.color,
    r.icon,
    r.inherits_from,
    r.is_template,
    r.created_at,
    pr.name as parent_name,
    COUNT(DISTINCT rf.feature_name) as direct_feature_count,
    COUNT(DISTINCT cr.client_id) as client_count
FROM rulesets r
LEFT JOIN rulesets pr ON r.inherits_from = pr.id
LEFT JOIN ruleset_features rf ON r.id = rf.ruleset_id AND rf.enabled = true
LEFT JOIN client_rulesets cr ON r.id = cr.ruleset_id
GROUP BY r.id, r.name, r.display_name, r.description, r.color, r.icon,
         r.inherits_from, r.is_template, r.created_at, pr.name;

-- View: Clients with their ruleset info and override counts
CREATE OR REPLACE VIEW client_summary AS
SELECT
    cr.client_id,
    cr.ruleset_id,
    r.name as ruleset_name,
    r.display_name as ruleset_display_name,
    r.color as ruleset_color,
    cr.assigned_at,
    cr.assigned_by,
    COUNT(DISTINCT co.id) as override_count
FROM client_rulesets cr
LEFT JOIN rulesets r ON cr.ruleset_id = r.id
LEFT JOIN client_overrides co ON cr.client_id = co.client_id
GROUP BY cr.client_id, cr.ruleset_id, r.name, r.display_name, r.color,
         cr.assigned_at, cr.assigned_by;

-- ============================================================================
-- Row Level Security (optional - enable if needed)
-- ============================================================================

-- Enable RLS on tables (uncomment if using Supabase auth)
-- ALTER TABLE feature_registry ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE rulesets ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE ruleset_features ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE client_rulesets ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE client_overrides ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE feature_audit_log ENABLE ROW LEVEL SECURITY;

-- ============================================================================
-- Seed Data: Default Template Rulesets
-- ============================================================================

-- Insert template rulesets (Starter, Professional, Enterprise)
INSERT INTO rulesets (name, display_name, description, color, icon, is_template, created_by)
VALUES
    ('starter', 'Starter Plan', 'Basic features for small teams', '#22c55e', 'rocket', true, 'system'),
    ('professional', 'Professional Plan', 'Advanced features for growing teams', '#3b82f6', 'briefcase', true, 'system'),
    ('enterprise', 'Enterprise Plan', 'Full access for large organizations', '#8b5cf6', 'building', true, 'system')
ON CONFLICT (name) DO NOTHING;

-- Set up inheritance chain: Enterprise -> Professional -> Starter
UPDATE rulesets SET inherits_from = (SELECT id FROM rulesets WHERE name = 'starter')
WHERE name = 'professional';

UPDATE rulesets SET inherits_from = (SELECT id FROM rulesets WHERE name = 'professional')
WHERE name = 'enterprise';

-- ============================================================================
-- Functions for Resolving Features
-- ============================================================================

-- Function to get all features for a ruleset (with inheritance)
CREATE OR REPLACE FUNCTION get_ruleset_features(p_ruleset_id UUID)
RETURNS TABLE (
    feature_name VARCHAR(100),
    enabled BOOLEAN,
    source_ruleset_id UUID,
    source_ruleset_name VARCHAR(100),
    is_inherited BOOLEAN
) AS $$
WITH RECURSIVE ruleset_chain AS (
    -- Base case: start with the given ruleset
    SELECT id, name, inherits_from, 0 as depth
    FROM rulesets
    WHERE id = p_ruleset_id

    UNION ALL

    -- Recursive case: follow inheritance chain
    SELECT r.id, r.name, r.inherits_from, rc.depth + 1
    FROM rulesets r
    INNER JOIN ruleset_chain rc ON r.id = rc.inherits_from
),
features_with_priority AS (
    SELECT
        rf.feature_name,
        rf.enabled,
        rc.id as source_ruleset_id,
        rc.name as source_ruleset_name,
        rc.depth,
        ROW_NUMBER() OVER (PARTITION BY rf.feature_name ORDER BY rc.depth) as rn
    FROM ruleset_chain rc
    JOIN ruleset_features rf ON rc.id = rf.ruleset_id
)
SELECT
    fwp.feature_name,
    fwp.enabled,
    fwp.source_ruleset_id,
    fwp.source_ruleset_name,
    (fwp.depth > 0) as is_inherited
FROM features_with_priority fwp
WHERE fwp.rn = 1;  -- Only return the most specific (lowest depth) setting
$$ LANGUAGE SQL STABLE;

-- Function to get resolved features for a client (with overrides)
CREATE OR REPLACE FUNCTION get_client_features(p_client_id VARCHAR(255))
RETURNS TABLE (
    feature_name VARCHAR(100),
    enabled BOOLEAN,
    source VARCHAR(50),  -- 'override', 'ruleset', or 'inherited'
    source_detail VARCHAR(255),
    expires_at TIMESTAMPTZ
) AS $$
WITH client_ruleset AS (
    SELECT ruleset_id FROM client_rulesets WHERE client_id = p_client_id
),
ruleset_features AS (
    SELECT
        grf.feature_name,
        grf.enabled,
        CASE WHEN grf.is_inherited THEN 'inherited' ELSE 'ruleset' END as source,
        grf.source_ruleset_name as source_detail,
        NULL::TIMESTAMPTZ as expires_at
    FROM client_ruleset cr
    CROSS JOIN LATERAL get_ruleset_features(cr.ruleset_id) grf
),
client_override_features AS (
    SELECT
        co.feature_name,
        co.enabled,
        'override'::VARCHAR(50) as source,
        co.reason as source_detail,
        co.expires_at
    FROM client_overrides co
    WHERE co.client_id = p_client_id
    AND (co.expires_at IS NULL OR co.expires_at > NOW())
),
all_features AS (
    SELECT * FROM ruleset_features
    UNION ALL
    SELECT * FROM client_override_features
),
prioritized AS (
    SELECT
        af.*,
        ROW_NUMBER() OVER (
            PARTITION BY af.feature_name
            ORDER BY CASE af.source
                WHEN 'override' THEN 1
                WHEN 'ruleset' THEN 2
                WHEN 'inherited' THEN 3
                ELSE 4
            END
        ) as rn
    FROM all_features af
)
SELECT
    p.feature_name,
    p.enabled,
    p.source,
    p.source_detail,
    p.expires_at
FROM prioritized p
WHERE p.rn = 1;
$$ LANGUAGE SQL STABLE;

-- Grant permissions (adjust based on your setup)
-- GRANT ALL ON ALL TABLES IN SCHEMA public TO authenticated;
-- GRANT ALL ON ALL FUNCTIONS IN SCHEMA public TO authenticated;
