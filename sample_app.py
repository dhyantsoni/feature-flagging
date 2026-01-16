"""
Sample application with feature-flagged functions to demonstrate the ruleset system.
This simulates a real application with nested function dependencies and dynamic feature flags.
"""

from feature_flag_client import FeatureFlagClient

# Initialize the feature flag client
# You can specify different rulesets: "production", "staging", "development", etc.
client = FeatureFlagClient(ruleset_name="development")


# Core utility functions
def database_query(query):
    """Simulate database query"""
    print(f"Executing query: {query}")
    return {"status": "success", "data": []}


def send_notification(user_id, message):
    """Send notification to user"""
    print(f"Sending notification to {user_id}: {message}")


def log_event(event_name, data):
    """Log event for analytics"""
    print(f"Logging event: {event_name} with data: {data}")


# Feature 1: New recommendation engine
def calculate_recommendations(user_id):
    """New recommendation algorithm (feature flagged)"""
    if not client.isEnabled("feature1_recommendations", {"user_id": user_id}):
        print(f"Feature1 disabled for user {user_id}, using legacy recommendation system")
        return {"recommendations": ["legacy1", "legacy2"]}

    user_data = fetch_user_preferences(user_id)
    recommendations = generate_recommendations(user_data)
    cache_recommendations(user_id, recommendations)
    return recommendations


def fetch_user_preferences(user_id):
    """Fetch user preferences from database"""
    result = database_query(f"SELECT * FROM preferences WHERE user_id={user_id}")
    return result


def generate_recommendations(user_data):
    """Generate recommendations based on user data"""
    # Complex recommendation logic
    recommendations = process_algorithm(user_data)
    return recommendations


def process_algorithm(data):
    """Process recommendation algorithm"""
    return {"recommendations": ["item1", "item2", "item3"]}


def cache_recommendations(user_id, recommendations):
    """Cache recommendations for faster access"""
    print(f"Caching recommendations for user {user_id}")


# Feature 2: Enhanced notification system
def send_enhanced_notification(user_id, message):
    """Enhanced notification with rich content (feature flagged)"""
    if not client.isEnabled("feature2_enhanced_notifications", {"user_id": user_id}):
        print(f"Feature2 disabled for user {user_id}, using basic notification")
        send_notification(user_id, message)
        return

    enriched_message = enrich_notification(message)
    delivery_method = determine_delivery_method(user_id)
    deliver_notification(user_id, enriched_message, delivery_method)
    track_notification_sent(user_id, message)


def enrich_notification(message):
    """Add rich content to notification"""
    return f"[ENHANCED] {message}"


def determine_delivery_method(user_id):
    """Determine best delivery method for user"""
    user_prefs = database_query(f"SELECT delivery_pref FROM users WHERE id={user_id}")
    return user_prefs.get("delivery_pref", "email")


def deliver_notification(user_id, message, method):
    """Deliver notification via specified method"""
    if method == "push":
        send_push_notification(user_id, message)
    else:
        send_email_notification(user_id, message)


def send_push_notification(user_id, message):
    """Send push notification"""
    print(f"Push notification to {user_id}: {message}")


def send_email_notification(user_id, message):
    """Send email notification"""
    print(f"Email to {user_id}: {message}")


def track_notification_sent(user_id, message):
    """Track that notification was sent"""
    log_event("notification_sent", {"user_id": user_id, "message": message})


# Feature 3: Advanced analytics
def generate_advanced_report(user_id):
    """Generate advanced analytics report (feature flagged)"""
    if not client.isEnabled("feature3_advanced_analytics", {"user_id": user_id}):
        print(f"Feature3 disabled for user {user_id}, using basic analytics")
        return {"summary": "Basic analytics report", "timestamp": "2026-01-16"}

    raw_data = collect_analytics_data(user_id)
    processed_data = process_analytics(raw_data)
    visualizations = create_visualizations(processed_data)
    report = compile_report(visualizations, processed_data)
    return report


def collect_analytics_data(user_id):
    """Collect analytics data for user"""
    return database_query(f"SELECT * FROM analytics WHERE user_id={user_id}")


def process_analytics(data):
    """Process raw analytics data"""
    return apply_statistical_models(data)


def apply_statistical_models(data):
    """Apply statistical models to data"""
    return {"mean": 50, "median": 45, "mode": 42}


def create_visualizations(data):
    """Create data visualizations"""
    return generate_charts(data)


def generate_charts(data):
    """Generate charts from data"""
    return ["chart1.png", "chart2.png"]


def compile_report(visualizations, data):
    """Compile final report"""
    return {
        "visualizations": visualizations,
        "summary": data,
        "timestamp": "2026-01-16"
    }


# Legacy function that should work regardless of feature flags
def get_basic_user_info(user_id):
    """Get basic user information (no feature flag)"""
    return database_query(f"SELECT * FROM users WHERE id={user_id}")


# Main entry point
def main():
    """Main application entry point"""
    print("=== Feature Flag Demo Application ===\n")
    print(f"Active ruleset: {client.ruleset_name}")
    print(f"Baseline configuration: {client.get_baseline()}\n")

    # Simulate different users
    test_users = [123, 456, 789]

    for user_id in test_users:
        print(f"\n--- Processing user {user_id} ---")

        # Call feature-flagged functions
        print(f"Recommendations: {calculate_recommendations(user_id)}")
        send_enhanced_notification(user_id, "You have new recommendations!")
        report = generate_advanced_report(user_id)
        print(f"Report: {report}")

        # Call non-flagged function
        user_info = get_basic_user_info(user_id)

    print("\n=== Testing different rulesets ===")

    # Test with production ruleset
    print("\nSwitching to 'production' ruleset...")
    client.switch_ruleset("production")
    user_id = 999
    print(f"User {user_id} - Recommendations: {calculate_recommendations(user_id)}")

    # Test with beta_testers ruleset (user 123 is whitelisted)
    print("\nSwitching to 'beta_testers' ruleset...")
    client.switch_ruleset("beta_testers")
    print(f"User 123 (whitelisted) - Recommendations: {calculate_recommendations(123)}")
    print(f"User 999 (not whitelisted) - Recommendations: {calculate_recommendations(999)}")

    # Test kill switch
    print("\n=== Testing Kill Switch ===")
    print("Activating kill switch...")
    client.activate_kill_switch()
    print(f"User 123 with kill switch - Recommendations: {calculate_recommendations(123)}")

    print("\n=== Application completed successfully ===")


if __name__ == "__main__":
    main()
