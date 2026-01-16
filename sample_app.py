"""
Sample application with feature-flagged functions to demonstrate static analysis.
This simulates a real application with nested function dependencies.
"""

# Simulated feature flag decorator (will be replaced with real implementation later)
def feature_flag(flag_name):
    def decorator(func):
        func._feature_flag = flag_name
        return func
    return decorator


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
@feature_flag("feature1_recommendations")
def calculate_recommendations(user_id):
    """New recommendation algorithm (feature flagged)"""
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
@feature_flag("feature2_enhanced_notifications")
def send_enhanced_notification(user_id, message):
    """Enhanced notification with rich content (feature flagged)"""
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
@feature_flag("feature3_advanced_analytics")
def generate_advanced_report(user_id):
    """Generate advanced analytics report (feature flagged)"""
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
    user_id = 123

    # Call feature-flagged functions
    recommendations = calculate_recommendations(user_id)
    send_enhanced_notification(user_id, "You have new recommendations!")
    report = generate_advanced_report(user_id)

    # Call non-flagged function
    user_info = get_basic_user_info(user_id)

    print("Application completed successfully")


if __name__ == "__main__":
    main()
