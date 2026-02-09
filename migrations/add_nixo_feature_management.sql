-- ============================================================================
-- NIXO FEATURE MANAGEMENT SYSTEM - COMPLETE MIGRATION
-- ============================================================================
-- This migration creates all tables and pre-populates with 23 features
-- discovered from nixo-custops codebase via AST analysis.
--
-- Run this ONCE in Supabase SQL Editor - it handles everything.
-- ============================================================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- CLEAN SLATE - Drop existing objects
-- ============================================================================
DROP TABLE IF EXISTS feature_audit_log CASCADE;i 
DROP TABLE IF EXISTS client_overrides CASCADE;
DROP TABLE IF EXISTS client_rulesets CASCADE;
DROP TABLE IF EXISTS ruleset_features CASCADE;
DROP TABLE IF EXISTS rulesets CASCADE;
DROP TABLE IF EXISTS feature_registry CASCADE;
DROP VIEW IF EXISTS ruleset_summary CASCADE;
DROP VIEW IF EXISTS client_summary CASCADE;
DROP FUNCTION IF EXISTS get_ruleset_features(UUID);
DROP FUNCTION IF EXISTS get_client_features(VARCHAR);
DROP FUNCTION IF EXISTS update_updated_at_column() CASCADE;

-- ============================================================================
-- TABLE: feature_registry
-- All 23 features from nixo-custops AVAILABLE_FEATURES
-- ============================================================================
CREATE TABLE feature_registry (
    name VARCHAR(100) PRIMARY KEY,
    description TEXT,
    category VARCHAR(50) NOT NULL,
    is_enforced BOOLEAN DEFAULT FALSE,
    enforcement_locations JSONB DEFAULT '[]',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_feature_registry_category ON feature_registry(category);

-- ============================================================================
-- TABLE: rulesets
-- Flexible rulesets with inheritance support
-- ============================================================================
CREATE TABLE rulesets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) UNIQUE NOT NULL,
    display_name VARCHAR(200) NOT NULL,
    description TEXT,
    color VARCHAR(7) DEFAULT '#6366f1',
    icon VARCHAR(50) DEFAULT 'package',
    inherits_from UUID REFERENCES rulesets(id) ON DELETE SET NULL,
    is_template BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by VARCHAR(100)
);

CREATE INDEX idx_rulesets_inherits_from ON rulesets(inherits_from);
CREATE INDEX idx_rulesets_is_template ON rulesets(is_template);

-- ============================================================================
-- TABLE: ruleset_features
-- Maps features to rulesets
-- ============================================================================
CREATE TABLE ruleset_features (
    ruleset_id UUID REFERENCES rulesets(id) ON DELETE CASCADE,
    feature_name VARCHAR(100) REFERENCES feature_registry(name) ON DELETE CASCADE,
    enabled BOOLEAN DEFAULT TRUE,
    config JSONB DEFAULT '{}',
    PRIMARY KEY (ruleset_id, feature_name)
);

CREATE INDEX idx_ruleset_features_feature ON ruleset_features(feature_name);

-- ============================================================================
-- TABLE: client_rulesets
-- Assigns rulesets to clients
-- ============================================================================
CREATE TABLE client_rulesets (
    client_id VARCHAR(255) PRIMARY KEY,
    ruleset_id UUID REFERENCES rulesets(id) ON DELETE SET NULL,
    assigned_at TIMESTAMPTZ DEFAULT NOW(),
    assigned_by VARCHAR(100),
    notes TEXT
);

CREATE INDEX idx_client_rulesets_ruleset ON client_rulesets(ruleset_id);

-- ============================================================================
-- TABLE: client_overrides
-- Per-client feature overrides (highest priority)
-- ============================================================================
CREATE TABLE client_overrides (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_id VARCHAR(255) NOT NULL,
    feature_name VARCHAR(100) REFERENCES feature_registry(name) ON DELETE CASCADE,
    enabled BOOLEAN NOT NULL,
    reason TEXT,
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    created_by VARCHAR(100),
    UNIQUE(client_id, feature_name)
);

CREATE INDEX idx_client_overrides_client ON client_overrides(client_id);
CREATE INDEX idx_client_overrides_feature ON client_overrides(feature_name);
CREATE INDEX idx_client_overrides_expires ON client_overrides(expires_at) WHERE expires_at IS NOT NULL;

-- ============================================================================
-- TABLE: feature_audit_log
-- Tracks all changes
-- ============================================================================
CREATE TABLE feature_audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    action VARCHAR(50) NOT NULL,
    entity_type VARCHAR(50),
    entity_id VARCHAR(255),
    changes JSONB,
    actor VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_feature_audit_log_entity ON feature_audit_log(entity_type, entity_id);
CREATE INDEX idx_feature_audit_log_action ON feature_audit_log(action);
CREATE INDEX idx_feature_audit_log_created ON feature_audit_log(created_at DESC);

-- ============================================================================
-- TRIGGER: Auto-update updated_at
-- ============================================================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_feature_registry_updated_at
    BEFORE UPDATE ON feature_registry
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_rulesets_updated_at
    BEFORE UPDATE ON rulesets
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- VIEWS
-- ============================================================================
CREATE VIEW ruleset_summary AS
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

CREATE VIEW client_summary AS
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
-- FUNCTIONS: Feature Resolution
-- ============================================================================
CREATE OR REPLACE FUNCTION get_ruleset_features(p_ruleset_id UUID)
RETURNS TABLE (
    feature_name VARCHAR(100),
    enabled BOOLEAN,
    source_ruleset_id UUID,
    source_ruleset_name VARCHAR(100),
    is_inherited BOOLEAN
) AS $$
WITH RECURSIVE ruleset_chain AS (
    SELECT id, name, inherits_from, 0 as depth
    FROM rulesets WHERE id = p_ruleset_id
    UNION ALL
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
SELECT fwp.feature_name, fwp.enabled, fwp.source_ruleset_id,
       fwp.source_ruleset_name, (fwp.depth > 0) as is_inherited
FROM features_with_priority fwp WHERE fwp.rn = 1;
$$ LANGUAGE SQL STABLE;

CREATE OR REPLACE FUNCTION get_client_features(p_client_id VARCHAR(255))
RETURNS TABLE (
    feature_name VARCHAR(100),
    enabled BOOLEAN,
    source VARCHAR(50),
    source_detail VARCHAR(255),
    expires_at TIMESTAMPTZ
) AS $$
WITH client_ruleset AS (
    SELECT ruleset_id FROM client_rulesets WHERE client_id = p_client_id
),
ruleset_features AS (
    SELECT grf.feature_name, grf.enabled,
           CASE WHEN grf.is_inherited THEN 'inherited' ELSE 'ruleset' END as source,
           grf.source_ruleset_name as source_detail,
           NULL::TIMESTAMPTZ as expires_at
    FROM client_ruleset cr
    CROSS JOIN LATERAL get_ruleset_features(cr.ruleset_id) grf
),
client_override_features AS (
    SELECT co.feature_name, co.enabled,
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
    SELECT af.*,
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
SELECT p.feature_name, p.enabled, p.source, p.source_detail, p.expires_at
FROM prioritized p WHERE p.rn = 1;
$$ LANGUAGE SQL STABLE;

-- ============================================================================
-- SEED DATA: All 23 Features from nixo-custops
-- ============================================================================

-- Account Management (4 features)
INSERT INTO feature_registry (name, description, category, is_enforced, enforcement_locations, metadata) VALUES
('accounts', 'Accounts management page', 'Account Management', false, '[]', '{"tier": "starter"}'),
('customer_dashboard', 'Customer dashboard view', 'Account Management', false, '[]', '{"tier": "starter"}'),
('schemas', 'Schemas configuration page', 'Account Management', false, '[]', '{"tier": "starter"}'),
('account_analysis', 'Account analysis and insights', 'Account Management', false, '[]', '{"tier": "professional"}');

-- AI Studio (3 features)
INSERT INTO feature_registry (name, description, category, is_enforced, enforcement_locations, metadata) VALUES
('intaker_agent', 'AI Intaker Agent for automated support intake', 'AI Studio', true,
 '[{"file": "slack_handler.py", "line": 907, "type": "runtime_check"},
   {"file": "services/AI_Intaker_agent/intaker_routes.py", "line": 21, "type": "decorator"},
   {"file": "services/AI_Intaker_agent/intaker_routes.py", "line": 43, "type": "decorator"},
   {"file": "services/AI_Intaker_agent/intaker_routes.py", "line": 101, "type": "decorator"},
   {"file": "services/AI_Intaker_agent/intaker_routes.py", "line": 439, "type": "decorator"}]',
 '{"tier": "enterprise", "critical": true}'),
('tickets', 'Tickets/Issues management', 'AI Studio', false, '[]', '{"tier": "starter"}'),
('testbed', 'AI Testbed for testing', 'AI Studio', false, '[]', '{"tier": "enterprise"}');

-- Communications (3 features)
INSERT INTO feature_registry (name, description, category, is_enforced, enforcement_locations, metadata) VALUES
('related_tickets', 'Related tickets view', 'Communications', false, '[]', '{"tier": "professional"}'),
('blasts', 'Broadcast/Blasts messaging', 'Communications', false, '[]', '{"tier": "professional"}'),
('digests', 'Digests and summaries', 'Communications', false, '[]', '{"tier": "professional"}');

-- Integrations (10 features)
INSERT INTO feature_registry (name, description, category, is_enforced, enforcement_locations, metadata) VALUES
('slack_settings', 'Slack integration settings', 'Integrations', false, '[]', '{"tier": "starter"}'),
('hubspot_integration', 'HubSpot CRM integration and notifications', 'Integrations', false, '[]', '{"tier": "professional"}'),
('linear_integration', 'Linear issue tracking integration', 'Integrations', false, '[]', '{"tier": "professional"}'),
('fireflies', 'Fireflies meeting integration', 'Integrations', false, '[]', '{"tier": "enterprise"}'),
('fathom', 'Fathom meeting integration', 'Integrations', false, '[]', '{"tier": "enterprise"}'),
('circleback', 'Circleback meeting integration', 'Integrations', false, '[]', '{"tier": "enterprise"}'),
('github_repos', 'GitHub indexed repositories', 'Integrations', false, '[]', '{"tier": "professional"}'),
('intercom', 'Intercom integration', 'Integrations', false, '[]', '{"tier": "professional"}'),
('github_oauth', 'GitHub OAuth integration', 'Integrations', false, '[]', '{"tier": "enterprise"}'),
('github_app', 'GitHub App integration', 'Integrations', false, '[]', '{"tier": "enterprise"}');

-- Advanced (3 features)
INSERT INTO feature_registry (name, description, category, is_enforced, enforcement_locations, metadata) VALUES
('custom_branding', 'Custom branding and white-labeling', 'Advanced', false, '[]', '{"tier": "enterprise"}'),
('advanced_analytics', 'Advanced analytics and reporting', 'Advanced', false, '[]', '{"tier": "enterprise"}'),
('api_access', 'API access for integrations', 'Advanced', false, '[]', '{"tier": "enterprise"}');

-- ============================================================================
-- SEED DATA: Template Rulesets (Starter -> Professional -> Enterprise)
-- ============================================================================

-- Create the three template rulesets
INSERT INTO rulesets (name, display_name, description, color, icon, is_template, created_by) VALUES
('starter', 'Starter Plan', 'Essential features for small teams getting started', '#22c55e', 'rocket', true, 'system'),
('professional', 'Professional Plan', 'Advanced features for growing teams', '#3b82f6', 'briefcase', true, 'system'),
('enterprise', 'Enterprise Plan', 'Full access with premium features for large organizations', '#8b5cf6', 'building', true, 'system');

-- Set up inheritance: Enterprise -> Professional -> Starter
UPDATE rulesets SET inherits_from = (SELECT id FROM rulesets WHERE name = 'starter')
WHERE name = 'professional';

UPDATE rulesets SET inherits_from = (SELECT id FROM rulesets WHERE name = 'professional')
WHERE name = 'enterprise';

-- ============================================================================
-- SEED DATA: Assign features to template rulesets
-- ============================================================================

-- STARTER PLAN (6 basic features)
INSERT INTO ruleset_features (ruleset_id, feature_name, enabled)
SELECT r.id, f.name, true
FROM rulesets r, feature_registry f
WHERE r.name = 'starter' AND f.name IN (
    'accounts',
    'customer_dashboard',
    'schemas',
    'tickets',
    'slack_settings',
    'intercom'
);

-- PROFESSIONAL PLAN (8 additional features - inherits starter's 6)
INSERT INTO ruleset_features (ruleset_id, feature_name, enabled)
SELECT r.id, f.name, true
FROM rulesets r, feature_registry f
WHERE r.name = 'professional' AND f.name IN (
    'account_analysis',
    'related_tickets',
    'blasts',
    'digests',
    'hubspot_integration',
    'linear_integration',
    'github_repos'
);

-- ENTERPRISE PLAN (9 additional features - inherits professional's 14)
INSERT INTO ruleset_features (ruleset_id, feature_name, enabled)
SELECT r.id, f.name, true
FROM rulesets r, feature_registry f
WHERE r.name = 'enterprise' AND f.name IN (
    'intaker_agent',
    'testbed',
    'fireflies',
    'fathom',
    'circleback',
    'github_oauth',
    'github_app',
    'custom_branding',
    'advanced_analytics',
    'api_access'
);

-- ============================================================================
-- VERIFICATION: Show what was created
-- ============================================================================
DO $$
DECLARE
    feature_count INTEGER;
    ruleset_count INTEGER;
    starter_features INTEGER;
    pro_features INTEGER;
    ent_features INTEGER;
BEGIN
    SELECT COUNT(*) INTO feature_count FROM feature_registry;
    SELECT COUNT(*) INTO ruleset_count FROM rulesets;
    SELECT COUNT(*) INTO starter_features FROM ruleset_features rf
        JOIN rulesets r ON rf.ruleset_id = r.id WHERE r.name = 'starter';
    SELECT COUNT(*) INTO pro_features FROM ruleset_features rf
        JOIN rulesets r ON rf.ruleset_id = r.id WHERE r.name = 'professional';
    SELECT COUNT(*) INTO ent_features FROM ruleset_features rf
        JOIN rulesets r ON rf.ruleset_id = r.id WHERE r.name = 'enterprise';

    RAISE NOTICE '============================================';
    RAISE NOTICE 'NIXO FEATURE MANAGEMENT - SETUP COMPLETE';
    RAISE NOTICE '============================================';
    RAISE NOTICE 'Features registered: %', feature_count;
    RAISE NOTICE 'Rulesets created: %', ruleset_count;
    RAISE NOTICE 'Starter plan: % direct features', starter_features;
    RAISE NOTICE 'Professional plan: % direct features (+ % inherited = % total)',
        pro_features, starter_features, pro_features + starter_features;
    RAISE NOTICE 'Enterprise plan: % direct features (+ % inherited = % total)',
        ent_features, pro_features + starter_features, ent_features + pro_features + starter_features;
    RAISE NOTICE '============================================';
END $$;
