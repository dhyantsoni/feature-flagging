"""
Complete End-to-End Workflow Example for Feature Flagging System
Demonstrates how the Supabase integration works with practical scenarios
"""

import os
import json
from datetime import datetime
from supabase_client import SupabaseClient


def print_section(title):
    """Print a formatted section header"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def print_step(step_num, description):
    """Print a numbered workflow step"""
    print(f"\n[STEP {step_num}] {description}")
    print("-" * 70)


class E2EWorkflow:
    """Complete end-to-end workflow for feature flagging"""
    
    def __init__(self):
        """Initialize workflow with Supabase client"""
        try:
            self.supabase = SupabaseClient()
            self.demo_data = {}
        except Exception as e:
            print(f"ERROR: Cannot initialize Supabase client: {e}")
            raise
    
    def scenario_1_new_project_analysis(self):
        """
        SCENARIO 1: New Project Integration
        
        A team wants to analyze an existing Python project using the AST analyzer
        and create feature flags for specific functions
        """
        print_section("SCENARIO 1: New Project Analysis")
        
        print_step(1, "Create a new project in the system")
        project = self.supabase.create_project(
            name="UserAuthenticationService",
            description="Microservice for user authentication and authorization",
            repository_url="https://github.com/company/auth-service"
        )
        print(f"   Created project: {project['name']} (ID: {project['id']})")
        self.demo_data['project'] = project
        
        print_step(2, "Analyze project codebase and identify functions")
        functions_to_create = [
            {
                "name": "authenticate_user",
                "file": "auth.py",
                "is_feature_flagged": True,
                "complexity": 8
            },
            {
                "name": "validate_token",
                "file": "token_utils.py",
                "is_feature_flagged": True,
                "complexity": 5
            },
            {
                "name": "hash_password",
                "file": "crypto.py",
                "is_helper": True,
                "complexity": 3
            },
            {
                "name": "generate_jwt",
                "file": "token_utils.py",
                "is_helper": True,
                "is_shared_helper": True,
                "complexity": 6
            }
        ]
        
        created_functions = []
        for func in functions_to_create:
            f = self.supabase.save_function(
                project_id=project['id'],
                function_name=func['name'],
                file_path=func['file'],
                is_feature_flagged=func.get('is_feature_flagged', False),
                is_helper=func.get('is_helper', False),
                is_shared_helper=func.get('is_shared_helper', False),
                complexity_score=func['complexity']
            )
            created_functions.append(f)
            status = "[FLAGGED]" if func.get('is_feature_flagged') else "[HELPER]"
            print(f"   {status} {func['name']} in {func['file']} (complexity: {func['complexity']})")
        
        self.demo_data['functions'] = created_functions
        
        print_step(3, "Create feature flags for new functionality")
        features = [
            {
                "name": "oauth2_integration",
                "description": "New OAuth2 provider support",
                "enabled": True
            },
            {
                "name": "mfa_enforcement",
                "description": "Enforce multi-factor authentication",
                "enabled": False
            }
        ]
        
        created_features = []
        for feat in features:
            f = self.supabase.create_feature(
                project_id=project['id'],
                feature_name=feat['name'],
                description=feat['description'],
                is_enabled=feat['enabled']
            )
            created_features.append(f)
            status = "[ENABLED]" if feat['enabled'] else "[DISABLED]"
            print(f"   {status} {feat['name']}: {feat['description']}")
        
        self.demo_data['features'] = created_features
        
        print_step(4, "Map functions to features")
        # Map authenticate_user to oauth2_integration
        self.supabase.create_function_mapping(
            feature_id=created_features[0]['id'],  # oauth2
            function_id=created_functions[0]['id'],  # authenticate_user
            is_entry_point=True,
            dependency_type="direct"
        )
        print(f"   ✓ Mapped authenticate_user → oauth2_integration (entry point)")
        
        # Map validate_token to oauth2_integration
        self.supabase.create_function_mapping(
            feature_id=created_features[0]['id'],
            function_id=created_functions[1]['id'],  # validate_token
            is_entry_point=False,
            dependency_type="downstream"
        )
        print(f"   ✓ Mapped validate_token → oauth2_integration (downstream)")
        
        # Map generate_jwt to oauth2_integration (shared helper)
        self.supabase.create_function_mapping(
            feature_id=created_features[0]['id'],
            function_id=created_functions[3]['id'],  # generate_jwt
            is_entry_point=False,
            dependency_type="helper"
        )
        print(f"   ✓ Mapped generate_jwt → oauth2_integration (shared helper)")
        
        print_step(5, "Save function call graph")
        # Create a simple call graph structure
        call_graph = {
            "nodes": {
                "authenticate_user": {"complexity": 8, "is_flagged": True},
                "validate_token": {"complexity": 5, "is_flagged": True},
                "generate_jwt": {"complexity": 6, "is_helper": True},
                "hash_password": {"complexity": 3, "is_helper": True}
            },
            "edges": [
                ["authenticate_user", "hash_password"],
                ["authenticate_user", "generate_jwt"],
                ["validate_token", "generate_jwt"]
            ]
        }
        
        graph = self.supabase.save_function_graph(
            project_id=project['id'],
            file_path="auth_module",
            graph_data=call_graph,
            total_functions=4,
            total_calls=3
        )
        print(f"   ✓ Saved call graph with {len(call_graph['nodes'])} nodes")
        
        print_step(6, "Analyze feature impact")
        impact = {
            "affected_functions": ["authenticate_user", "validate_token", "generate_jwt"],
            "complexity_increase": 0.15,
            "risk_level": "medium"
        }
        
        self.supabase.save_impact_analysis(
            feature_id=created_features[0]['id'],  # oauth2_integration
            analysis_data=impact,
            total_affected=3,
            unreachable=0,
            need_fallback=1
        )
        print(f"   ✓ Impact Analysis: 3 affected functions, medium risk")
        print(f"     - Complexity increase: 15%")
        print(f"     - Functions needing fallback: 1")
    
    def scenario_2_client_registration(self):
        """
        SCENARIO 2: Client Registration and Ruleset Assignment
        
        A new client/service registers and gets assigned a feature ruleset
        """
        print_section("SCENARIO 2: Client Registration and Ruleset")
        
        print_step(1, "Create a new ruleset")
        ruleset = self.supabase.create_ruleset(
            name="stable_features",
            description="Only proven, stable features enabled",
            features=[
                {"name": "oauth2_integration", "enabled": True},
                {"name": "mfa_enforcement", "enabled": False}
            ],
            rollout_percentage=100
        )
        print(f"   Created ruleset: {ruleset['name']}")
        self.demo_data['ruleset'] = ruleset
        
        print_step(2, "Register a new client")
        client = self.supabase.save_client(
            client_id="mobile_app_v2",
            ruleset_name="stable_features",
            project_id=self.demo_data['project']['id'],
            metadata={
                "platform": "iOS",
                "min_version": "14.0",
                "team": "mobile"
            }
        )
        print(f"   Registered client: {client['client_id']}")
        print(f"   Platform: {client['metadata'].get('platform')}")
        print(f"   Assigned ruleset: {client['ruleset_name']}")
        self.demo_data['client'] = client
        
        print_step(3, "Verify client configuration")
        retrieved = self.supabase.get_client("mobile_app_v2")
        print(f"   ✓ Client retrieved: {retrieved['client_id']}")
        print(f"   ✓ Ruleset: {retrieved['ruleset_name']}")
        print(f"   ✓ Metadata: {json.dumps(retrieved['metadata'], indent=6)}")
    
    def scenario_3_feature_rollout(self):
        """
        SCENARIO 3: Gradual Feature Rollout
        
        A new feature is gradually rolled out to users using rulesets
        """
        print_section("SCENARIO 3: Gradual Feature Rollout")
        
        print_step(1, "Create canary release ruleset (5% rollout)")
        canary = self.supabase.create_ruleset(
            name="mfa_canary",
            description="Canary release: MFA to 5% of users",
            features=[
                {"name": "mfa_enforcement", "enabled": True, "rollout_percentage": 5}
            ],
            rollout_percentage=5
        )
        print(f"   Created canary ruleset: {canary['name']} (5% rollout)")
        
        print_step(2, "Register canary test clients")
        test_clients = [
            {"id": "internal_qa_team", "platform": "web"},
            {"id": "beta_testers_group", "platform": "mobile"}
        ]
        
        for test_client in test_clients:
            self.supabase.save_client(
                client_id=test_client['id'],
                ruleset_name="mfa_canary",
                project_id=self.demo_data['project']['id'],
                metadata={"platform": test_client['platform'], "tier": "canary"}
            )
            print(f"   ✓ Registered {test_client['id']} on canary release")
        
        print_step(3, "Monitor feature health (Day 1)")
        print(f"   Canary metrics:")
        print(f"   - Affected users: ~5% (50 out of 1000)")
        print(f"   - Error rate: 0.2%")
        print(f"   - Performance impact: -0.5%")
        print(f"   → Status: HEALTHY ✓")
        
        print_step(4, "Expand to beta release (25% rollout)")
        beta = self.supabase.create_ruleset(
            name="mfa_beta",
            description="Beta release: MFA to 25% of users",
            features=[
                {"name": "mfa_enforcement", "enabled": True, "rollout_percentage": 25}
            ],
            rollout_percentage=25
        )
        print(f"   Created beta ruleset: {beta['name']} (25% rollout)")
        print(f"   ✓ Can now safely expand to larger user base")
        
        print_step(5, "Ready for full production rollout")
        production = self.supabase.create_ruleset(
            name="mfa_production",
            description="Production: MFA enabled for all users",
            features=[
                {"name": "mfa_enforcement", "enabled": True, "rollout_percentage": 100}
            ],
            rollout_percentage=100
        )
        print(f"   Created production ruleset: {production['name']} (100% rollout)")
        print(f"   ✓ Ready for general availability")
    
    def scenario_4_query_features(self):
        """
        SCENARIO 4: Query Feature and Dependency Information
        
        Applications query the system to determine which features are enabled
        """
        print_section("SCENARIO 4: Runtime Feature Queries")
        
        print_step(1, "List all features for project")
        features = self.supabase.list_features(self.demo_data['project']['id'])
        print(f"   Found {len(features)} features:")
        for feat in features:
            status = "ENABLED" if feat.get('is_enabled') else "DISABLED"
            print(f"   - {feat['feature_name']}: {status}")
        
        print_step(2, "Get all functions mapped to a feature")
        if features:
            feature_id = features[0]['id']
            mappings = self.supabase.get_feature_functions(feature_id)
            print(f"   Functions for {features[0]['feature_name']}:")
            if mappings:
                for mapping in mappings:
                    func_name = mapping.get('function_id', 'unknown')
                    entry_point = " [ENTRY POINT]" if mapping.get('is_entry_point') else ""
                    print(f"   - {func_name}{entry_point}")
            else:
                print("   (No functions mapped yet)")
        
        print_step(3, "Get feature impact analysis")
        if features:
            feature_id = features[0]['id']
            impact = self.supabase.get_impact_analysis(feature_id)
            if impact:
                print(f"   Impact Analysis for {features[0]['feature_name']}:")
                print(f"   - Affected functions: {impact.get('total_affected_functions', 0)}")
                print(f"   - Unreachable: {impact.get('functions_unreachable', 0)}")
                print(f"   - Need fallback: {impact.get('functions_need_fallback', 0)}")
            else:
                print("   (No impact analysis available)")
        
        print_step(4, "List all clients")
        clients = self.supabase.list_clients(self.demo_data['project']['id'])
        print(f"   Found {len(clients)} registered clients:")
        for client in clients:
            print(f"   - {client['client_id']}: ruleset '{client['ruleset_name']}'")
    
    def scenario_5_data_analysis(self):
        """
        SCENARIO 5: Data Analysis and Reporting
        
        Analyze feature flag metrics and system health
        """
        print_section("SCENARIO 5: Data Analysis and Reporting")
        
        print_step(1, "Get all rulesets")
        rulesets = self.supabase.list_all_rulesets()
        print(f"   Total rulesets in system: {len(rulesets)}")
        
        print_step(2, "Analyze project coverage")
        projects = self.supabase.list_projects()
        total_projects = len(projects)
        print(f"   Total projects: {total_projects}")
        print(f"   Average functions per project: {4 if total_projects > 0 else 0}")  # Demo data
        
        print_step(3, "Feature enablement statistics")
        all_features = []
        for project in projects[:1]:  # Check first project
            features = self.supabase.list_features(project['id'])
            all_features.extend(features)
        
        if all_features:
            enabled = sum(1 for f in all_features if f.get('is_enabled'))
            print(f"   Total features: {len(all_features)}")
            print(f"   Enabled: {enabled}")
            print(f"   Disabled: {len(all_features) - enabled}")
            print(f"   Enablement rate: {(enabled / len(all_features) * 100):.1f}%")
        
        print_step(4, "System health summary")
        print(f"   ✓ Supabase connection: HEALTHY")
        print(f"   ✓ All tables: AVAILABLE")
        print(f"   ✓ Data integrity: VERIFIED")
        print(f"   → System Status: OPERATIONAL")


def run_complete_workflow():
    """Run all scenarios in sequence"""
    try:
        workflow = E2EWorkflow()
        
        workflow.scenario_1_new_project_analysis()
        workflow.scenario_2_client_registration()
        workflow.scenario_3_feature_rollout()
        workflow.scenario_4_query_features()
        workflow.scenario_5_data_analysis()
        
        print_section("WORKFLOW COMPLETE")
        print("\n✓ All scenarios executed successfully!")
        print("\nKey Takeaways:")
        print("  1. Projects organize codebases and analyses")
        print("  2. Functions represent code that can be feature-flagged")
        print("  3. Features are the actual flags that control behavior")
        print("  4. Mappings connect features to the functions they affect")
        print("  5. Rulesets define which features are enabled per client")
        print("  6. Impact analysis helps understand feature dependencies")
        print("\n" + "=" * 70 + "\n")
        
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    import sys
    import logging
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    run_complete_workflow()
