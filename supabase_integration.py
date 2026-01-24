"""
Supabase Integration Setup and Validation
Provides utilities for initializing and testing Supabase connection
"""

import os
import logging
from typing import Dict, List, Tuple, Optional
from supabase_client import SupabaseClient

logger = logging.getLogger(__name__)


class SupabaseIntegration:
    """Manages Supabase integration setup and validation"""

    def __init__(self):
        """Initialize Supabase integration checker"""
        self.supabase = None
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.checks_passed = 0
        self.checks_failed = 0

    def check_environment(self) -> bool:
        """Check if environment variables are set correctly"""
        logger.info("Checking environment variables...")
        
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_KEY")
        
        if not url:
            self.errors.append("❌ SUPABASE_URL environment variable not set")
            self.checks_failed += 1
            return False
        
        if not key:
            self.errors.append("❌ SUPABASE_KEY environment variable not set")
            self.checks_failed += 1
            return False
        
        if not url.startswith("https://"):
            self.errors.append(f"❌ SUPABASE_URL should start with https:// (got: {url})")
            self.checks_failed += 1
            return False
        
        logger.info(f"✓ Environment variables set: {url[:30]}...")
        self.checks_passed += 1
        return True

    def check_connection(self) -> bool:
        """Test connection to Supabase"""
        logger.info("Checking Supabase connection...")
        
        try:
            self.supabase = SupabaseClient()
            logger.info("✓ Supabase client initialized successfully")
            self.checks_passed += 1
            return True
        except Exception as e:
            self.errors.append(f"❌ Failed to connect to Supabase: {str(e)}")
            self.checks_failed += 1
            return False

    def check_tables(self) -> bool:
        """Verify all required tables exist"""
        logger.info("Checking database tables...")
        
        if not self.supabase:
            self.errors.append("❌ Cannot check tables - Supabase not connected")
            self.checks_failed += 1
            return False
        
        required_tables = [
            "projects",
            "functions",
            "features",
            "function_mappings",
            "dependencies",
            "impact_analysis",
            "clients",
            "rulesets",
            "function_graphs"
        ]
        
        tables_found = 0
        for table_name in required_tables:
            try:
                result = self.supabase.client.table(table_name).select("*").limit(0).execute()
                tables_found += 1
                logger.info(f"  ✓ Table '{table_name}' exists")
            except Exception as e:
                self.errors.append(f"❌ Table '{table_name}' not found: {str(e)}")
        
        if tables_found == len(required_tables):
            logger.info(f"✓ All {len(required_tables)} required tables exist")
            self.checks_passed += 1
            return True
        else:
            self.checks_failed += 1
            return False

    def test_crud_operations(self) -> bool:
        """Test basic CRUD operations"""
        logger.info("Testing CRUD operations...")
        
        if not self.supabase:
            self.errors.append("❌ Cannot test CRUD - Supabase not connected")
            self.checks_failed += 1
            return False
        
        try:
            # Test create project
            test_project = self.supabase.create_project(
                name="test_project_" + str(os.getpid()),
                description="Test project for validation"
            )
            
            if not test_project:
                self.errors.append("❌ Failed to create test project")
                self.checks_failed += 1
                return False
            
            project_id = test_project['id']
            logger.info(f"  ✓ Created test project: {project_id}")
            
            # Test read
            retrieved = self.supabase.get_project(project_id)
            if not retrieved:
                self.errors.append("❌ Failed to read test project")
                self.checks_failed += 1
                return False
            
            logger.info(f"  ✓ Retrieved test project: {retrieved['name']}")
            
            # Test update (via save_function_graph which uses insert)
            test_graph_data = {
                "nodes": {"func1": {"type": "test"}},
                "edges": []
            }
            graph = self.supabase.save_function_graph(
                project_id=project_id,
                file_path="test.py",
                graph_data=test_graph_data,
                total_functions=1,
                total_calls=0
            )
            
            if not graph:
                self.errors.append("❌ Failed to save function graph")
                self.checks_failed += 1
                return False
            
            logger.info(f"  ✓ Saved function graph")
            
            # Test list
            projects = self.supabase.list_projects()
            if not isinstance(projects, list):
                self.errors.append("❌ Failed to list projects")
                self.checks_failed += 1
                return False
            
            logger.info(f"  ✓ Listed projects: {len(projects)} total")
            
            logger.info("✓ All CRUD operations successful")
            self.checks_passed += 1
            return True
            
        except Exception as e:
            self.errors.append(f"❌ CRUD test failed: {str(e)}")
            self.checks_failed += 1
            return False

    def print_report(self) -> None:
        """Print validation report"""
        print("\n" + "=" * 60)
        print("SUPABASE INTEGRATION VALIDATION REPORT")
        print("=" * 60)
        
        if self.errors:
            print("\n❌ ERRORS:")
            for error in self.errors:
                print(f"  {error}")
        
        if self.warnings:
            print("\n⚠️  WARNINGS:")
            for warning in self.warnings:
                print(f"  {warning}")
        
        if not self.errors and not self.warnings:
            print("\n✅ All checks passed!")
        
        print(f"\nSummary: {self.checks_passed} passed, {self.checks_failed} failed")
        print("=" * 60 + "\n")

    def run_all_checks(self) -> bool:
        """Run all validation checks"""
        logger.info("Starting Supabase integration validation...")
        
        all_passed = True
        all_passed &= self.check_environment()
        
        if all_passed:
            all_passed &= self.check_connection()
        
        if all_passed:
            all_passed &= self.check_tables()
        
        if all_passed:
            all_passed &= self.test_crud_operations()
        
        self.print_report()
        return len(self.errors) == 0


def validate_supabase_integration() -> bool:
    """
    Standalone validation function for Supabase integration
    Returns True if all checks pass
    """
    validator = SupabaseIntegration()
    return validator.run_all_checks()


def create_demo_data() -> Dict:
    """
    Create demo data for testing the system
    Returns metadata about created demo objects
    """
    logger.info("Creating demo data...")
    
    try:
        supabase = SupabaseClient()
    except Exception as e:
        logger.error(f"Cannot create demo data - Supabase not available: {e}")
        return {}
    
    demo_data = {}
    
    try:
        # Create demo project
        project = supabase.create_project(
            name="Demo E-commerce Platform",
            description="Example project showing feature flagging with AST analysis",
            repository_url="https://github.com/example/ecommerce"
        )
        demo_data['project'] = project
        logger.info(f"Created demo project: {project['id']}")
        
        # Create demo functions
        functions_data = [
            {
                "name": "process_payment",
                "description": "Main payment processing function",
                "is_feature_flagged": True
            },
            {
                "name": "validate_card",
                "description": "Card validation helper",
                "is_helper": True
            },
            {
                "name": "apply_discount",
                "description": "Apply discount to order",
                "is_feature_flagged": True
            }
        ]
        
        functions_created = []
        for func_data in functions_data:
            func = supabase.save_function(
                project_id=project['id'],
                function_name=func_data['name'],
                file_path="payment.py",
                is_feature_flagged=func_data.get('is_feature_flagged', False),
                is_helper=func_data.get('is_helper', False),
                complexity_score=5
            )
            functions_created.append(func)
            logger.info(f"Created function: {func_data['name']}")
        
        demo_data['functions'] = functions_created
        
        # Create demo features
        features_data = [
            {
                "name": "stripe_payments",
                "description": "New Stripe payment integration"
            },
            {
                "name": "loyalty_discounts",
                "description": "Customer loyalty discount program"
            }
        ]
        
        features_created = []
        for feat_data in features_data:
            feature = supabase.create_feature(
                project_id=project['id'],
                feature_name=feat_data['name'],
                description=feat_data['description'],
                is_enabled=True
            )
            features_created.append(feature)
            logger.info(f"Created feature: {feat_data['name']}")
        
        demo_data['features'] = features_created
        
        logger.info("✓ Demo data created successfully")
        
    except Exception as e:
        logger.error(f"Failed to create demo data: {e}")
    
    return demo_data


if __name__ == "__main__":
    import sys
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run validation
    is_valid = validate_supabase_integration()
    
    # If valid and requested, create demo data
    if is_valid and len(sys.argv) > 1 and sys.argv[1] == "--create-demo":
        create_demo_data()
    
    sys.exit(0 if is_valid else 1)
