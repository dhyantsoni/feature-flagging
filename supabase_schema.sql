-- Feature Flagging System - Supabase Schema
-- This schema supports AST-based function graph analysis and feature management

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Projects table: Store analyzed codebases
CREATE TABLE projects (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    repository_url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Function graphs table: Store complete call graph analysis
CREATE TABLE function_graphs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    graph_data JSONB NOT NULL, -- Full NetworkX graph structure
    analysis_timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    file_path TEXT NOT NULL,
    total_functions INTEGER NOT NULL DEFAULT 0,
    total_calls INTEGER NOT NULL DEFAULT 0,
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Functions table: Individual function metadata
CREATE TABLE functions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    function_name VARCHAR(500) NOT NULL,
    file_path TEXT NOT NULL,
    is_feature_flagged BOOLEAN DEFAULT FALSE,
    is_helper BOOLEAN DEFAULT FALSE,
    is_shared_helper BOOLEAN DEFAULT FALSE, -- Used by multiple features
    line_number INTEGER,
    complexity_score INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb,
    UNIQUE(project_id, function_name)
);

-- Features table: Feature flag definitions
CREATE TABLE features (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    feature_name VARCHAR(255) NOT NULL,
    description TEXT,
    is_enabled BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb,
    UNIQUE(project_id, feature_name)
);

-- Function mappings: Feature-to-function relationships
CREATE TABLE function_mappings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    feature_id UUID REFERENCES features(id) ON DELETE CASCADE,
    function_id UUID REFERENCES functions(id) ON DELETE CASCADE,
    is_entry_point BOOLEAN DEFAULT FALSE, -- Main feature-flagged function
    dependency_type VARCHAR(50) NOT NULL, -- 'direct', 'downstream', 'upstream', 'helper'
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(feature_id, function_id)
);

-- Dependencies table: Function call relationships
CREATE TABLE dependencies (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    caller_function_id UUID REFERENCES functions(id) ON DELETE CASCADE,
    callee_function_id UUID REFERENCES functions(id) ON DELETE CASCADE,
    call_count INTEGER DEFAULT 1,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(caller_function_id, callee_function_id)
);

-- Impact analysis: Cached feature impact results
CREATE TABLE impact_analysis (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    feature_id UUID REFERENCES features(id) ON DELETE CASCADE,
    analysis_data JSONB NOT NULL,
    total_affected_functions INTEGER DEFAULT 0,
    functions_unreachable INTEGER DEFAULT 0,
    functions_need_fallback INTEGER DEFAULT 0,
    analyzed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Clients table: Client configurations (from existing system)
CREATE TABLE clients (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    client_id VARCHAR(255) NOT NULL UNIQUE,
    project_id UUID REFERENCES projects(id) ON DELETE SET NULL,
    ruleset_name VARCHAR(255) NOT NULL,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Rulesets table: Feature flag ruleset configurations
CREATE TABLE rulesets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    ruleset_name VARCHAR(255) NOT NULL,
    description TEXT,
    rules JSONB NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(project_id, ruleset_name)
);

-- Create indexes for performance
CREATE INDEX idx_functions_project ON functions(project_id);
CREATE INDEX idx_functions_feature_flagged ON functions(is_feature_flagged);
CREATE INDEX idx_functions_helper ON functions(is_helper);
CREATE INDEX idx_function_mappings_feature ON function_mappings(feature_id);
CREATE INDEX idx_function_mappings_function ON function_mappings(function_id);
CREATE INDEX idx_dependencies_caller ON dependencies(caller_function_id);
CREATE INDEX idx_dependencies_callee ON dependencies(callee_function_id);
CREATE INDEX idx_function_graphs_project ON function_graphs(project_id);
CREATE INDEX idx_features_project ON features(project_id);
CREATE INDEX idx_clients_project ON clients(project_id);
CREATE INDEX idx_rulesets_project ON rulesets(project_id);

-- Create updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply updated_at triggers
CREATE TRIGGER update_projects_updated_at BEFORE UPDATE ON projects
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_features_updated_at BEFORE UPDATE ON features
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_clients_updated_at BEFORE UPDATE ON clients
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_rulesets_updated_at BEFORE UPDATE ON rulesets
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Row Level Security (RLS) Policies
ALTER TABLE projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE function_graphs ENABLE ROW LEVEL SECURITY;
ALTER TABLE functions ENABLE ROW LEVEL SECURITY;
ALTER TABLE features ENABLE ROW LEVEL SECURITY;
ALTER TABLE function_mappings ENABLE ROW LEVEL SECURITY;
ALTER TABLE dependencies ENABLE ROW LEVEL SECURITY;
ALTER TABLE impact_analysis ENABLE ROW LEVEL SECURITY;
ALTER TABLE clients ENABLE ROW LEVEL SECURITY;
ALTER TABLE rulesets ENABLE ROW LEVEL SECURITY;

-- Allow all operations for authenticated users (adjust based on your auth setup)
CREATE POLICY "Allow all for authenticated users" ON projects FOR ALL USING (auth.role() = 'authenticated');
CREATE POLICY "Allow all for authenticated users" ON function_graphs FOR ALL USING (auth.role() = 'authenticated');
CREATE POLICY "Allow all for authenticated users" ON functions FOR ALL USING (auth.role() = 'authenticated');
CREATE POLICY "Allow all for authenticated users" ON features FOR ALL USING (auth.role() = 'authenticated');
CREATE POLICY "Allow all for authenticated users" ON function_mappings FOR ALL USING (auth.role() = 'authenticated');
CREATE POLICY "Allow all for authenticated users" ON dependencies FOR ALL USING (auth.role() = 'authenticated');
CREATE POLICY "Allow all for authenticated users" ON impact_analysis FOR ALL USING (auth.role() = 'authenticated');
CREATE POLICY "Allow all for authenticated users" ON clients FOR ALL USING (auth.role() = 'authenticated');
CREATE POLICY "Allow all for authenticated users" ON rulesets FOR ALL USING (auth.role() = 'authenticated');

-- Allow read access for anon users (public API access)
CREATE POLICY "Allow read for anon" ON projects FOR SELECT USING (true);
CREATE POLICY "Allow read for anon" ON functions FOR SELECT USING (true);
CREATE POLICY "Allow read for anon" ON features FOR SELECT USING (true);
CREATE POLICY "Allow read for anon" ON clients FOR SELECT USING (true);
CREATE POLICY "Allow read for anon" ON rulesets FOR SELECT USING (true);
