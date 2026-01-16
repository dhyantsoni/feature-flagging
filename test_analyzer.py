"""
Test suite for Feature Flag Analyzer
"""

import json
from feature_flag_analyzer import FeatureFlagAnalyzer


def test_feature_flag_extraction():
    """Test that feature flags are correctly extracted from source code"""
    analyzer = FeatureFlagAnalyzer("callgraph.json", "sample_app.py")

    expected_flags = {
        "sample_app.calculate_recommendations": "feature1_recommendations",
        "sample_app.send_enhanced_notification": "feature2_enhanced_notifications",
        "sample_app.generate_advanced_report": "feature3_advanced_analytics"
    }

    assert analyzer.feature_flags == expected_flags, \
        f"Expected {expected_flags}, got {analyzer.feature_flags}"
    print("✅ Feature flag extraction test passed")


def test_downstream_dependencies():
    """Test downstream dependency detection"""
    analyzer = FeatureFlagAnalyzer("callgraph.json", "sample_app.py")

    # Test feature1: calculate_recommendations
    downstream = analyzer.get_downstream_dependencies("sample_app.calculate_recommendations")
    downstream.discard("sample_app.calculate_recommendations")

    expected = {
        "sample_app.fetch_user_preferences",
        "sample_app.database_query",
        "sample_app.generate_recommendations",
        "sample_app.process_algorithm",
        "sample_app.cache_recommendations"
    }

    assert downstream == expected, \
        f"Expected {expected}, got {downstream}"
    print("✅ Downstream dependencies test passed")


def test_upstream_dependencies():
    """Test upstream dependency detection"""
    analyzer = FeatureFlagAnalyzer("callgraph.json", "sample_app.py")

    # Test that main() calls the feature-flagged function
    upstream = analyzer.get_upstream_dependencies("sample_app.calculate_recommendations")

    assert "sample_app.main" in upstream, \
        f"Expected 'sample_app.main' in upstream dependencies, got {upstream}"
    print("✅ Upstream dependencies test passed")


def test_impact_analysis():
    """Test full impact analysis"""
    analyzer = FeatureFlagAnalyzer("callgraph.json", "sample_app.py")

    results = analyzer.analyze_feature_impact("feature1_recommendations")

    assert "sample_app.calculate_recommendations" in results
    func_data = results["sample_app.calculate_recommendations"]

    # Check that summary exists and has expected keys
    assert "impact_summary" in func_data
    summary = func_data["impact_summary"]

    assert summary["functions_that_become_unreachable"] == 5, \
        f"Expected 5 unreachable functions, got {summary['functions_that_become_unreachable']}"

    assert summary["functions_needing_fallback_logic"] == 1, \
        f"Expected 1 function needing fallback, got {summary['functions_needing_fallback_logic']}"

    print("✅ Impact analysis test passed")


def test_nested_dependencies():
    """Test that nested dependencies are properly detected"""
    analyzer = FeatureFlagAnalyzer("callgraph.json", "sample_app.py")

    # feature1 -> fetch_user_preferences -> database_query
    # Ensure database_query is detected as a downstream dependency
    downstream = analyzer.get_downstream_dependencies("sample_app.calculate_recommendations")

    assert "sample_app.database_query" in downstream, \
        "Nested dependency 'database_query' should be detected"
    print("✅ Nested dependencies test passed")


def test_shared_dependencies():
    """Test handling of shared dependencies across features"""
    analyzer = FeatureFlagAnalyzer("callgraph.json", "sample_app.py")

    # database_query is used by multiple features
    # Check which features use it
    features_using_db = []

    for flag_name in ["feature1_recommendations", "feature2_enhanced_notifications",
                      "feature3_advanced_analytics"]:
        results = analyzer.analyze_feature_impact(flag_name)
        for func, data in results.items():
            if "sample_app.database_query" in data["downstream_dependencies"]:
                features_using_db.append(flag_name)

    assert len(features_using_db) == 3, \
        f"database_query should be used by 3 features, found in {len(features_using_db)}"
    print("✅ Shared dependencies test passed")


def test_non_flagged_function():
    """Test analysis of non-feature-flagged function"""
    analyzer = FeatureFlagAnalyzer("callgraph.json", "sample_app.py")

    # get_basic_user_info is not feature-flagged
    downstream = analyzer.get_downstream_dependencies("sample_app.get_basic_user_info")
    downstream.discard("sample_app.get_basic_user_info")

    # Should only have database_query as downstream
    assert "sample_app.database_query" in downstream
    print("✅ Non-flagged function test passed")


def run_all_tests():
    """Run all test cases"""
    print("=" * 80)
    print("RUNNING FEATURE FLAG ANALYZER TESTS")
    print("=" * 80)
    print()

    tests = [
        test_feature_flag_extraction,
        test_downstream_dependencies,
        test_upstream_dependencies,
        test_impact_analysis,
        test_nested_dependencies,
        test_shared_dependencies,
        test_non_flagged_function
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            print(f"\nRunning: {test.__name__}")
            print("-" * 80)
            test()
            passed += 1
        except AssertionError as e:
            print(f"❌ Test failed: {e}")
            failed += 1
        except Exception as e:
            print(f"❌ Test error: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print("\n" + "=" * 80)
    print(f"TEST RESULTS: {passed} passed, {failed} failed")
    print("=" * 80)

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
