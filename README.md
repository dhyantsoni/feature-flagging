# Feature Flagging System with Ruleset Engine

A comprehensive feature flagging system with dynamic polling, A/B testing, percentage rollouts, user targeting, and kill switch functionality.

## Features

- **Dynamic Ruleset System**: Define and manage multiple rulesets for different environments
- **Percentage Rollouts**: Gradually roll out features to a percentage of users with consistent hashing
- **A/B Testing**: Assign users to test groups consistently
- **User Targeting**: Target specific users or user attributes with whitelists/blacklists
- **Kill Switch**: Instantly disable all features and revert to baseline behavior
- **Multi-level Caching**: In-memory → File cache → Bootstrap defaults for offline-first operation
- **Dynamic Polling**: Optional background polling for real-time configuration updates
- **Supabase Integration**: Optional remote feature flag management (framework ready)

## Installation

```bash
pip install -r requirements.txt
```

## Quick Start

```python
from feature_flag_client import FeatureFlagClient

# Initialize the client with a ruleset
client = FeatureFlagClient(ruleset_name="production")

# Check if a feature is enabled for a user
if client.isEnabled("feature1_recommendations", {"user_id": 123}):
    # Use new feature
    pass
else:
    # Use baseline/legacy code
    pass
```

## Configuration

### Rulesets (rulesets.yaml)

Rulesets define how features should be evaluated. Each ruleset includes:

- **type**: `percentage`, `user_targeting`, or `ab_test`
- **kill_switch_active**: Boolean to enable/disable all features
- **baseline**: Fallback values when features are disabled
- **features**: Feature-specific configuration

Example:

```yaml
production:
  type: percentage
  kill_switch_active: false
  baseline:
    feature1_recommendations: false
    feature2_enhanced_notifications: false
  features:
    feature1_recommendations:
      enabled: true
      percentage: 25  # Roll out to 25% of users
    feature2_enhanced_notifications:
      enabled: true
      percentage: 50
```

### Bootstrap Defaults (bootstrap_defaults.json)

Provides offline fallback configuration in JSON format. Used when:
- Network is unavailable (Supabase)
- Local YAML file is missing
- File cache is corrupted

## Ruleset Types

### 1. Percentage Rollout

Uses consistent hashing to ensure the same user always gets the same result:

```yaml
production:
  type: percentage
  features:
    new_feature:
      enabled: true
      percentage: 25  # 25% of users
```

### 2. User Targeting

Target specific users or user attributes:

```yaml
beta_testers:
  type: user_targeting
  features:
    new_feature:
      enabled: true
      whitelist: [123, 456, 789]  # Specific user IDs
      target_attributes:
        tier: ["premium", "enterprise"]
        beta_tester: true
```

### 3. A/B Testing

Assign users to groups consistently:

```yaml
ab_test_recommendations:
  type: ab_test
  features:
    new_recommendations:
      enabled: true
      groups: ["control", "treatment"]
      treatment_groups: ["treatment"]
```

## Usage Examples

### Basic Usage

```python
from feature_flag_client import FeatureFlagClient

client = FeatureFlagClient(ruleset_name="development")

# Check feature for a specific user
user_context = {"user_id": 123, "tier": "premium"}

if client.isEnabled("feature1_recommendations", user_context):
    result = calculate_new_recommendations(user_id)
else:
    result = calculate_legacy_recommendations(user_id)
```

### Switching Rulesets

```python
# Start with production ruleset
client = FeatureFlagClient(ruleset_name="production")

# Switch to a different ruleset at runtime
client.switch_ruleset("staging")
```

### Kill Switch

```python
# Activate kill switch - all features revert to baseline
client.activate_kill_switch()

# Deactivate kill switch - resume normal evaluation
client.deactivate_kill_switch()
```

### Dynamic Polling

```python
# Enable background polling for configuration updates
client = FeatureFlagClient(
    ruleset_name="production",
    enable_polling=True,
    polling_interval=60  # Check for updates every 60 seconds
)

# Polling runs in background, configuration auto-updates
```

### Supabase Integration

```python
from supabase import create_client

supabase = create_client(url, key)

client = FeatureFlagClient(
    ruleset_name="production",
    supabase_client=supabase,
    enable_polling=True
)

# Client will poll Supabase for configuration updates
```

### Context Manager

```python
# Automatically cleanup resources (stop polling threads)
with FeatureFlagClient(ruleset_name="production") as client:
    if client.isEnabled("new_feature", {"user_id": 123}):
        # Use feature
        pass
```

## Running the Demo

```bash
python sample_app.py
```

The demo application showcases:
- Multiple feature flags with nested dependencies
- Different ruleset evaluations
- User targeting (whitelists)
- Percentage-based rollouts
- Kill switch functionality
- Baseline fallback behavior

## Architecture

### Configuration Loading Priority

1. **Supabase** (if configured) - Remote configuration
2. **Local YAML file** (rulesets.yaml) - Local configuration
3. **File cache** (.feature_flags_cache.json) - Cached configuration
4. **Bootstrap defaults** (bootstrap_defaults.json) - Offline fallback

### Caching Layers

- **In-memory cache**: Fast evaluation during runtime
- **File cache**: Persists configuration across restarts
- **Bootstrap defaults**: Bundled defaults for offline scenarios

## API Reference

### FeatureFlagClient

#### `__init__(ruleset_name, config_path, bootstrap_path, cache_file_path, polling_interval, enable_polling, supabase_client)`

Initialize the feature flag client.

#### `isEnabled(feature_name, user_context) -> bool`

Check if a feature is enabled for the given user context.

- **feature_name**: Name of the feature to check
- **user_context**: Dictionary with user info (`user_id`, attributes, etc.)
- **Returns**: True if enabled, False otherwise

#### `activate_kill_switch()`

Activate kill switch - revert all features to baseline.

#### `deactivate_kill_switch()`

Deactivate kill switch - resume normal evaluation.

#### `switch_ruleset(ruleset_name)`

Switch to a different ruleset.

#### `get_baseline() -> Dict[str, bool]`

Get baseline configuration for active ruleset.

#### `reload_configuration()`

Manually reload configuration from all sources.

## File Structure

```
feature-flagging/
├── feature_flag_client.py      # Main client implementation
├── ruleset_engine.py            # Core ruleset evaluation logic
├── rulesets.yaml                # Ruleset configurations
├── bootstrap_defaults.json      # Offline fallback defaults
├── sample_app.py                # Demo application
├── requirements.txt             # Python dependencies
└── README.md                    # This file
```

## Future Enhancements

- Static analysis integration for dependency detection (PyCG)
- Dashboard for ruleset management
- Analytics for feature usage tracking
- Webhook support for real-time updates
- Multi-region configuration sync

## License

MIT
