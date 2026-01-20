# Ruleset Architecture: Comprehensive Guide

## Table of Contents
1. [Core Concept](#core-concept)
2. [Architecture Overview](#architecture-overview)
3. [How Rulesets Work](#how-rulesets-work)
4. [Client-Ruleset Relationship](#client-ruleset-relationship)
5. [Baseline Fallback Strategy](#baseline-fallback-strategy)
6. [Feature Access Flow](#feature-access-flow)
7. [Use Cases & Scenarios](#use-cases--scenarios)
8. [Configuration Deep Dive](#configuration-deep-dive)
9. [Advanced Features](#advanced-features)
10. [Best Practices](#best-practices)

---

## Core Concept

### What is a Ruleset?

A **ruleset** is a **defined set of features** that clients are granted access to. Think of it as a subscription tier or plan that determines which functionality a client can use in your application.

### Key Principle

```
Client → Assigned to Ruleset → Ruleset Contains Features → Client Can Access Those Features
```

**NOT**: ~~"Features have rules about which users see them"~~ ❌

**YES**: **"Clients have rulesets that define their available features"** ✅

### Real-World Analogy

Imagine a software company with subscription tiers:

- **Free Plan** (Ruleset) → Limited features (5 features)
- **Pro Plan** (Ruleset) → More features (14 features)
- **Enterprise Plan** (Ruleset) → All features (23 features)

Each **customer** (client) subscribes to a **plan** (ruleset), which determines what they can use.

---

## Architecture Overview

### Component Hierarchy

```
┌─────────────────────────────────────────────────┐
│              Application Layer                  │
│  (Your code checks: isEnabled(client, feature)) │
└───────────────────┬─────────────────────────────┘
                    │
┌───────────────────▼─────────────────────────────┐
│         Feature Flag Client API                 │
│  - isEnabled(client_id, feature_name)           │
│  - get_client_features(client_id)               │
│  - update_client_ruleset(client_id, new_set)    │
└───────────────────┬─────────────────────────────┘
                    │
┌───────────────────▼─────────────────────────────┐
│            Ruleset Engine                       │
│  - Maps clients → rulesets                      │
│  - Evaluates feature access                     │
│  - Handles baseline fallback                    │
│  - Manages kill switch                          │
└───────────────────┬─────────────────────────────┘
                    │
        ┌───────────┴───────────┐
        │                       │
┌───────▼────────┐    ┌────────▼─────────┐
│  Rulesets      │    │   Clients        │
│  (YAML)        │    │   (YAML)         │
│                │    │                  │
│ - baseline     │    │ - acme_corp:     │
│ - free_tier    │    │     enterprise   │
│ - starter      │    │ - small_biz:     │
│ - professional │    │     free_tier    │
│ - enterprise   │    │ - startup_co:    │
│ - beta         │    │     professional │
└────────────────┘    └──────────────────┘
```

---

## How Rulesets Work

### 1. Ruleset Definition

A ruleset is defined in `rulesets.yaml` and contains:

- **Name**: Unique identifier (e.g., `enterprise_tier`)
- **Description**: Human-readable explanation
- **Features**: List or dictionary of features included
- **Baseline Ruleset**: (Optional) Fallback ruleset if feature fails

**Example:**

```yaml
enterprise_tier:
  description: "Enterprise tier with all features"
  baseline_ruleset: baseline
  features:
    - basic_dashboard
    - enhanced_dashboard
    - enterprise_dashboard
    - advanced_analytics
    - sso_authentication
    - api_access
    # ... 17+ more features
```

### 2. Client Assignment

Each client is assigned to **exactly one ruleset** in `clients.yaml`:

```yaml
acme_corp:
  ruleset: enterprise_tier  # ← Client's assigned ruleset
  metadata:
    name: "Acme Corporation"
    tier: "Enterprise"
    contact: "admin@acme.com"
```

### 3. Feature Access Evaluation

When your application checks if a feature is enabled:

```python
client = FeatureFlagClient()
enabled = client.isEnabled("acme_corp", "advanced_analytics")
```

**What happens internally:**

1. Look up `acme_corp` → Find assigned ruleset: `enterprise_tier`
2. Check if `advanced_analytics` is in `enterprise_tier` features
3. If yes → Return `True`
4. If no → Check baseline ruleset → Return result

---

## Client-Ruleset Relationship

### One-to-One Mapping

Each client has **one active ruleset** at any time.

```
Client A → Ruleset 1 (Free Tier)
Client B → Ruleset 2 (Pro Tier)
Client C → Ruleset 3 (Enterprise Tier)
Client D → Ruleset 1 (Free Tier)  ← Multiple clients can share a ruleset
```

### Ruleset Changes (Upgrades/Downgrades)

Changing a client's ruleset is **instantaneous** and **easy**:

**Method 1: Edit YAML**
```yaml
# clients.yaml
small_biz_llc:
  ruleset: starter_tier  # Change from free_tier → starter_tier
```

**Method 2: Use API**
```bash
curl -X PUT http://localhost:5000/api/client/small_biz_llc/ruleset \
  -H "Content-Type: application/json" \
  -d '{"ruleset": "starter_tier"}'
```

**Method 3: Use Dashboard**
- Select client → Click "Change Ruleset" → Choose new ruleset → Update

### Lifecycle Example

```
Day 1:  small_biz_llc → free_tier (5 features)
        └─ Has: basic_dashboard, user_management, basic_reports

Day 30: Customer upgrades
        small_biz_llc → starter_tier (9 features)
        └─ Has: basic_dashboard, enhanced_dashboard, advanced_reports, ...

Day 60: Customer upgrades again
        small_biz_llc → professional_tier (14 features)
        └─ Has: All starter features + custom_reports, advanced_analytics, ...
```

---

## Baseline Fallback Strategy

### Purpose

The **baseline ruleset** ensures that even when advanced features fail, clients still have access to **core functionality**.

### How It Works

Every ruleset can specify a `baseline_ruleset`:

```yaml
enterprise_tier:
  baseline_ruleset: baseline  # ← Falls back to this if feature unavailable
  features:
    # ... 23 advanced features

baseline:
  features:
    - basic_dashboard      # ← Core features that ALWAYS work
    - user_management
    - basic_reports
    - profile_settings
```

### Fallback Scenarios

#### Scenario 1: Feature Not in Ruleset

```python
# Client has 'starter_tier' which doesn't include 'enterprise_dashboard'
enabled = client.isEnabled("techstart_inc", "enterprise_dashboard")

# Flow:
# 1. Check starter_tier → Feature NOT found
# 2. Check starter_tier's baseline → baseline ruleset
# 3. Check baseline → Feature NOT found
# Result: False
```

#### Scenario 2: Feature Exists in Ruleset

```python
# Client has 'enterprise_tier' which includes 'advanced_analytics'
enabled = client.isEnabled("acme_corp", "advanced_analytics")

# Flow:
# 1. Check enterprise_tier → Feature FOUND
# Result: True
```

#### Scenario 3: Kill Switch Activated

```python
# Kill switch is activated - all clients use baseline ONLY
client.activate_kill_switch()

enabled = client.isEnabled("acme_corp", "enterprise_dashboard")
# Result: False (not in baseline)

enabled = client.isEnabled("acme_corp", "basic_dashboard")
# Result: True (in baseline)
```

---

## Feature Access Flow

### Complete Decision Tree

```
┌─────────────────────────────────────┐
│  Application calls:                 │
│  isEnabled(client_id, feature_name) │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────┐
│  Is Kill Switch Active?     │
└────┬────────────────────┬───┘
     │ Yes                │ No
     │                    │
     ▼                    ▼
┌──────────────┐    ┌─────────────────────┐
│ Check        │    │ Lookup Client       │
│ Baseline     │    │ → Get Ruleset       │
│ Only         │    └──────────┬──────────┘
└──────────────┘               │
     │                         ▼
     │              ┌────────────────────────┐
     │              │ Feature in Ruleset?    │
     │              └────┬──────────────┬────┘
     │                   │ Yes          │ No
     │                   │              │
     │                   ▼              ▼
     │         ┌──────────────┐  ┌──────────────┐
     │         │ Has          │  │ Check        │
     │         │ Percentage?  │  │ Baseline     │
     │         └────┬────┬────┘  │ Ruleset      │
     │              │    │       └──────┬───────┘
     │              │ No │ Yes          │
     │              │    │              │
     │              ▼    ▼              │
     │         ┌─────────────────┐      │
     │         │ Return TRUE     │      │
     │         └─────────────────┘      │
     │              ▲                   │
     │              │                   │
     └──────────────┴───────────────────┘
                    │
                    ▼
         ┌─────────────────────┐
         │ Return TRUE/FALSE   │
         └─────────────────────┘
```

### Code Example with Flow

```python
# Setup
client = FeatureFlagClient()

# Example 1: Feature exists in client's ruleset
result = client.isEnabled("acme_corp", "advanced_analytics")
# acme_corp → enterprise_tier → has advanced_analytics → True

# Example 2: Feature NOT in client's ruleset
result = client.isEnabled("small_biz_llc", "advanced_analytics")
# small_biz_llc → free_tier → no advanced_analytics
# → Check baseline → no advanced_analytics → False

# Example 3: Baseline feature
result = client.isEnabled("small_biz_llc", "basic_dashboard")
# small_biz_llc → free_tier → has basic_dashboard → True

# Example 4: Kill switch active
client.activate_kill_switch()
result = client.isEnabled("acme_corp", "enterprise_dashboard")
# Kill switch → Check baseline only → no enterprise_dashboard → False
```

---

## Use Cases & Scenarios

### Use Case 1: SaaS Subscription Tiers

**Scenario**: You run a SaaS platform with Free, Pro, and Enterprise plans.

**Rulesets:**

```yaml
baseline:
  features: [basic_dashboard, profile, basic_reports]

free_tier:
  baseline_ruleset: baseline
  features:
    - basic_dashboard
    - profile
    - basic_reports
    - email_support

pro_tier:
  baseline_ruleset: baseline
  features:
    # All free features plus:
    - advanced_reports
    - api_access
    - priority_support
    - custom_branding

enterprise_tier:
  baseline_ruleset: baseline
  features:
    # All pro features plus:
    - sso_authentication
    - audit_logs
    - dedicated_support
    - unlimited_users
```

**Client Assignment:**

```yaml
clients:
  startup_co:
    ruleset: free_tier

  growing_company:
    ruleset: pro_tier

  big_corp:
    ruleset: enterprise_tier
```

**In Your Application:**

```python
if client.isEnabled(company_id, "sso_authentication"):
    show_sso_login()  # Only enterprise clients see this
else:
    show_standard_login()  # Everyone else
```

### Use Case 2: Beta Testing New Features

**Scenario**: You're testing a new AI-powered feature with select customers.

**Rulesets:**

```yaml
beta_tier:
  baseline_ruleset: professional_tier  # Beta testers get pro features + experimental
  features:
    # All professional features
    - advanced_reports
    - custom_reports
    # Plus experimental:
    - ai_insights:
        enabled: true
        percentage: 50  # Gradual rollout to 50% of beta users
    - experimental_dashboard
```

**Client Assignment:**

```yaml
beta_tester_1:
  ruleset: beta_tier
  metadata:
    name: "Beta Company"
    is_beta: true
```

**In Your Application:**

```python
# Check with user context for percentage rollout
if client.isEnabled("beta_tester_1", "ai_insights", {"user_id": 42}):
    show_ai_insights()  # User 42 might see this (50% chance, consistent)
```

### Use Case 3: Emergency Situation

**Scenario**: A critical bug is discovered in the `predictive_analytics` feature at 3 AM.

**Response:**

```python
# Option 1: Activate kill switch (all clients → baseline only)
client.activate_kill_switch()
# Now ALL clients only have: basic_dashboard, user_management, basic_reports, profile_settings

# Option 2: Create emergency ruleset without problematic feature
# Edit rulesets.yaml, remove predictive_analytics from all rulesets

# Option 3: Downgrade affected clients
for client_id in affected_clients:
    client.update_client_ruleset(client_id, "baseline")
```

**Result**: No complete outage! Users can still access core features while you fix the bug.

### Use Case 4: Gradual Feature Rollout

**Scenario**: Rolling out a new dashboard to minimize risk.

**Week 1:**
```yaml
professional_tier:
  features:
    new_dashboard:
      enabled: true
      percentage: 10  # 10% of users
```

**Week 2:** (After monitoring metrics)
```yaml
professional_tier:
  features:
    new_dashboard:
      enabled: true
      percentage: 50  # Increase to 50%
```

**Week 3:** (Everything looks good)
```yaml
professional_tier:
  features:
    new_dashboard: true  # 100% rollout
```

### Use Case 5: Custom Client Requirements

**Scenario**: A large client has a custom contract with specific features.

**Solution:**

```yaml
custom_acme_ruleset:
  baseline_ruleset: baseline
  features:
    # Standard features
    - basic_dashboard
    - advanced_reports
    # Custom requested features
    - custom_integration_feature
    - white_labeling
    - dedicated_api_endpoint
    # But NOT:
    # - Some features they don't need/want
```

```yaml
acme_mega_corp:
  ruleset: custom_acme_ruleset  # Client gets their custom feature set
```

---

## Configuration Deep Dive

### Ruleset Configuration Format

#### Simple Feature List

```yaml
baseline:
  description: "Core features"
  features:
    - basic_dashboard
    - user_management
    - basic_reports
    - profile_settings
```

**All features in the list are enabled by default.**

#### Advanced Feature Configuration

```yaml
professional_tier:
  description: "Professional tier features"
  baseline_ruleset: baseline
  features:
    basic_dashboard: true  # Simple enable

    enhanced_dashboard:
      enabled: true
      percentage: 100  # 100% rollout

    user_management:
      enabled: true
      max_users: 100  # Custom metadata

    api_access:
      enabled: true
      rate_limit: 10000  # Custom metadata
      endpoints: ["v1", "v2"]  # Custom metadata

    experimental_feature:
      enabled: true
      percentage: 25  # Gradual rollout
```

#### Percentage Rollout Details

```yaml
beta_feature:
  enabled: true
  percentage: 30  # Only 30% of users will see this
```

**How it works:**
- Uses MD5 hash of `client_id:user_id:feature_name`
- Deterministic: Same user always gets same result
- Distributed: ~30% of users will see the feature

**Usage:**

```python
# Must provide user_context for percentage rollout
if client.isEnabled("company_id", "beta_feature", {"user_id": 123}):
    show_beta_feature()
```

### Client Configuration Format

```yaml
client_id:
  ruleset: ruleset_name  # Required: Which ruleset they use
  metadata:              # Optional: Any additional info
    name: "Client Name"
    tier: "Enterprise"
    contact: "email@domain.com"
    signup_date: "2024-01-15"
    custom_field: "custom_value"
```

**The `ruleset` field is the ONLY thing that matters for feature access.**

Metadata is just for your reference and dashboard display.

---

## Advanced Features

### 1. Nested Baseline Fallbacks

You can create a **chain of fallbacks**:

```yaml
enterprise_tier:
  baseline_ruleset: professional_tier  # Falls back to pro
  features: [...]

professional_tier:
  baseline_ruleset: starter_tier  # Falls back to starter
  features: [...]

starter_tier:
  baseline_ruleset: baseline  # Falls back to baseline
  features: [...]

baseline:
  # No baseline - this is the end of the chain
  features: [...]
```

**Evaluation:**
```
1. Check enterprise_tier → Feature not found
2. Fall back to professional_tier → Feature not found
3. Fall back to starter_tier → Feature not found
4. Fall back to baseline → Feature found OR return False
```

### 2. Percentage Rollout with Consistent Hashing

**The Problem**: Random percentage rollouts mean users see different features on each page load.

**The Solution**: Consistent hashing ensures same user + feature always gives same result.

**Implementation:**

```python
# Hash input: "client_id:user_id:feature_name"
hash_input = "acme_corp:user_123:experimental_feature"
hash_value = MD5(hash_input) % 100  # Results in 0-99

# If hash_value <= percentage, feature is enabled
if hash_value <= 30:  # 30% rollout
    return True
```

**Result**: User 123 will **always** see (or not see) the feature consistently.

### 3. Kill Switch Mechanism

**Global Kill Switch** = Activate baseline fallback for **ALL clients**.

```python
# Emergency: Disable all non-critical features
client.activate_kill_switch()

# All clients now only have baseline features:
# - basic_dashboard
# - user_management
# - basic_reports
# - profile_settings

# Issue resolved, restore normal operation
client.deactivate_kill_switch()
```

**Use cases:**
- Critical bug in advanced features
- Database overload → Disable heavy features
- Security incident → Reduce attack surface
- Maintenance window

### 4. Dynamic Client Registration

**API Method:**

```bash
curl -X POST http://localhost:5000/api/client \
  -H "Content-Type: application/json" \
  -d '{
    "client_id": "new_client_co",
    "ruleset": "starter_tier",
    "metadata": {
      "name": "New Client Co",
      "contact": "admin@newclient.com"
    }
  }'
```

**Python Method:**

```python
client.register_client(
    "new_client_co",
    "starter_tier",
    metadata={"name": "New Client Co"}
)
```

**Result**: Client immediately has access to all `starter_tier` features.

### 5. Feature Metadata

You can attach metadata to features for custom logic:

```yaml
api_access:
  enabled: true
  rate_limit: 10000
  allowed_methods: ["GET", "POST", "PUT"]
  max_requests_per_minute: 1000
```

**Access in your application:**

```python
# Check if client has API access
if client.isEnabled("acme_corp", "api_access"):
    # Get the feature config for rate limiting
    ruleset = client.engine.rulesets[client_ruleset]
    feature_config = ruleset.features.get("api_access")
    rate_limit = feature_config.get("rate_limit", 1000)

    enforce_rate_limit(rate_limit)
```

---

## Best Practices

### 1. Keep Baseline Minimal

**DO:**
```yaml
baseline:
  features:
    - login
    - basic_dashboard
    - profile
    - logout
```

**DON'T:**
```yaml
baseline:
  features:
    - login
    - basic_dashboard
    - advanced_reports  # ❌ Too advanced for baseline
    - ai_insights       # ❌ Not critical
    - export_data       # ❌ Nice-to-have
```

**Why:** Baseline should only include features users **absolutely need** to use your app.

### 2. Progressive Enhancement

Design rulesets in a **tiered progression**:

```
baseline (4 features)
  ↓ Add 5 more
free_tier (5 features)
  ↓ Add 9 more
starter_tier (9 features)
  ↓ Add 14 more
professional_tier (14 features)
  ↓ Add 23 more
enterprise_tier (23 features)
```

### 3. Test in Beta First

Before promoting features to production:

```yaml
# Week 1: Beta testing
beta_tier:
  features:
    new_feature:
      percentage: 25  # Limited rollout

# Week 2: Expand
beta_tier:
  features:
    new_feature:
      percentage: 100  # Full beta rollout

# Week 3: Promote to production tiers if successful
professional_tier:
  features:
    new_feature: true
```

### 4. Clear Naming Conventions

**DO:**
- `baseline` - Core features
- `free_tier` - Free plan
- `starter_tier` - Entry plan
- `professional_tier` - Mid-tier plan
- `enterprise_tier` - Full-featured plan
- `beta_tier` - Testing features

**DON'T:**
- `ruleset_1`, `ruleset_2` - Not descriptive
- `temp_rules` - Unclear purpose
- `johns_special_rules` - Not maintainable

### 5. Document Feature Purposes

```yaml
professional_tier:
  features:
    advanced_analytics: true  # For power users who need detailed insights
    export_data: true         # Business requirement: GDPR data portability
    api_access: true          # For integrations with third-party tools
```

### 6. Monitor and Audit

**Track:**
- Which clients are on which rulesets
- Feature usage per ruleset
- Upgrade/downgrade patterns
- Kill switch activations

**Log:**
```python
# Log ruleset changes
def update_client_ruleset(client_id, new_ruleset):
    old_ruleset = get_current_ruleset(client_id)
    # ... update logic
    log.info(f"Client {client_id}: {old_ruleset} → {new_ruleset}")
```

### 7. Version Control Your Rulesets

```bash
# Commit changes to rulesets
git add rulesets.yaml clients.yaml
git commit -m "Add new AI feature to professional tier"

# Use branches for testing
git checkout -b test/new-feature-rollout
# Edit rulesets.yaml
# Test
# Merge to main
```

### 8. Graceful Degradation

Always provide a fallback for disabled features:

```python
if client.isEnabled(client_id, "advanced_analytics"):
    return render_advanced_analytics()
else:
    return render_basic_analytics()  # ← Always have a fallback!
```

**Never:**
```python
if client.isEnabled(client_id, "advanced_analytics"):
    return render_advanced_analytics()
else:
    return "Feature not available"  # ❌ Bad UX
```

---

## Summary

### Key Takeaways

1. **Rulesets = Feature Sets**: Clients are assigned to rulesets that define their available features
2. **One Ruleset Per Client**: Each client has exactly one active ruleset
3. **Baseline for Safety**: All rulesets fall back to baseline on failure
4. **Easy to Change**: Update `clients.yaml` or use API/dashboard to change rulesets
5. **Kill Switch**: Emergency fallback to baseline for ALL clients
6. **Percentage Rollouts**: Gradual feature deployment with consistent hashing
7. **No Complex Rules**: Simple, clear, maintainable configuration

### When to Use This System

✅ SaaS platforms with subscription tiers
✅ Multi-tenant applications with different feature sets
✅ Applications needing graceful degradation
✅ Systems requiring emergency kill switches
✅ Gradual feature rollouts to minimize risk
✅ Beta testing with select customers

### When NOT to Use This System

❌ Simple on/off feature flags (use a simpler system)
❌ User-level permissions (use a permissions system)
❌ A/B testing framework (this supports it but isn't optimized for it)
❌ Real-time collaborative editing (needs different architecture)

---

**This ruleset system provides a robust, maintainable approach to managing feature access across multiple clients with safety guarantees and easy configuration.**
