"""
Test script for the feature flag system
"""

from feature_flag_client import FeatureFlagClient

def test_system():
    print("=" * 60)
    print("Feature Flag System Test")
    print("=" * 60)

    # Initialize client
    print("\n1. Initializing Feature Flag Client...")
    client = FeatureFlagClient()
    print("   ✓ Client initialized successfully")

    # Load rulesets
    print("\n2. Loaded Rulesets:")
    rulesets = client.get_all_rulesets()
    for name, info in rulesets.items():
        print(f"   - {name}: {info['description']}")
        print(f"     Features: {len(info['features'])} features")

    # Load clients
    print("\n3. Loaded Clients:")
    clients = client.get_all_clients()
    for client_id, client_data in clients.items():
        metadata = client_data.get('metadata', {})
        print(f"   - {client_id}")
        print(f"     Name: {metadata.get('name', 'N/A')}")
        print(f"     Ruleset: {client_data.get('ruleset')}")
        print(f"     Tier: {metadata.get('tier', 'N/A')}")

    # Test feature access for different clients
    print("\n4. Testing Feature Access:")

    test_cases = [
        ("acme_corp", "enterprise_dashboard", True),
        ("acme_corp", "sso_authentication", True),
        ("techstart_inc", "enterprise_dashboard", False),
        ("techstart_inc", "enhanced_dashboard", True),
        ("small_biz_llc", "advanced_reports", False),
        ("small_biz_llc", "basic_dashboard", True),
    ]

    for client_id, feature, expected in test_cases:
        result = client.isEnabled(client_id, feature)
        status = "✓" if result == expected else "✗"
        print(f"   {status} {client_id} -> {feature}: {result} (expected: {expected})")

    # Test baseline fallback
    print("\n5. Testing Baseline Fallback:")
    print("   Activating kill switch...")
    client.activate_kill_switch()

    # All clients should now only have baseline features
    result = client.isEnabled("acme_corp", "enterprise_dashboard")
    print(f"   - acme_corp -> enterprise_dashboard: {result} (should be False)")

    result = client.isEnabled("acme_corp", "basic_dashboard")
    print(f"   - acme_corp -> basic_dashboard: {result} (should be True - baseline)")

    print("   Deactivating kill switch...")
    client.deactivate_kill_switch()

    # Test getting all features for a client
    print("\n6. Getting All Features for acme_corp:")
    features = client.get_client_features("acme_corp")
    print(f"   Total features: {len(features)}")
    print(f"   Features: {', '.join(sorted(list(features))[:10])}...")

    # Test percentage rollout
    print("\n7. Testing Percentage Rollout (beta_tier):")
    beta_client = "beta_tester_1"
    experimental_enabled_count = 0

    for user_id in range(100):
        if client.isEnabled(beta_client, "experimental_dashboard", {"user_id": user_id}):
            experimental_enabled_count += 1

    print(f"   experimental_dashboard enabled for {experimental_enabled_count}% of users")
    print(f"   (configured for 50% rollout)")

    # Test updating ruleset
    print("\n8. Testing Ruleset Update:")
    print("   Updating small_biz_llc from free_tier to starter_tier...")
    success = client.update_client_ruleset("small_biz_llc", "starter_tier")

    if success:
        print("   ✓ Ruleset updated successfully")
        features_before = ["basic_dashboard", "basic_reports"]
        has_advanced = client.isEnabled("small_biz_llc", "advanced_reports")
        print(f"   - advanced_reports now available: {has_advanced}")

        # Revert back
        client.update_client_ruleset("small_biz_llc", "free_tier")
        print("   Reverted back to free_tier")

    print("\n" + "=" * 60)
    print("All Tests Completed!")
    print("=" * 60)

if __name__ == "__main__":
    test_system()
