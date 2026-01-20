# Feature Flag Management System

A comprehensive client-based feature flagging system with ruleset management, baseline fallback, and a functional web dashboard.

## 🎯 Core Concept

**Rulesets define feature sets that clients can access.** Each client is assigned to a ruleset (tier), and if a feature fails or the kill switch is activated, clients automatically fall back to a baseline ruleset with core functionality.

### Key Features

✅ **Client-Ruleset Mapping**: Assign clients to rulesets (Free, Starter, Professional, Enterprise, Beta, Custom)  
✅ **Baseline Fallback**: Automatic fallback to core features when things go wrong  
✅ **Kill Switch**: Instantly revert ALL clients to baseline features  
✅ **Percentage Rollouts**: Gradual feature rollouts with consistent hashing  
✅ **Web Dashboard**: Functional UI to manage clients, rulesets, and test features  
✅ **REST API**: Full API for integration with your application  
✅ **Easy Configuration**: Simple YAML files for rulesets and clients  

---

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Start the Dashboard

```bash
python3 app.py
```

The dashboard will be available at **http://localhost:5000**

### 3. Use in Your Application

```python
from feature_flag_client import FeatureFlagClient

# Initialize client
ff_client = FeatureFlagClient()

# Check if a feature is enabled for a client
if ff_client.isEnabled("acme_corp", "advanced_analytics"):
    # Show advanced analytics
    show_advanced_analytics()
else:
    # Show basic analytics (baseline)
    show_basic_analytics()
```

---

## 📁 Project Structure

```
feature-flagging/
├── app.py                      # Flask backend + API
├── feature_flag_client.py      # Main client library
├── ruleset_engine.py           # Core ruleset evaluation logic
├── rulesets.yaml               # Ruleset definitions (feature sets)
├── clients.yaml                # Client-to-ruleset assignments
├── bootstrap_defaults.json     # Offline fallback configuration
├── test_system.py              # Comprehensive test suite
├── templates/
│   └── index.html              # Dashboard UI
└── static/
    ├── css/style.css           # Dashboard styling
    └── js/dashboard.js         # Dashboard functionality
```

---

## 🎨 Dashboard Features

Access at **http://localhost:5000** after starting the Flask app.

The web dashboard provides a complete interface for managing your feature flag system:

### 1. **Client Management**
   - View all registered clients
   - See assigned rulesets and available features
   - Search and filter clients
   - Add new clients dynamically

### 2. **Ruleset Management**
   - Change client rulesets with one click
   - View all available rulesets
   - See feature counts per ruleset

### 3. **Feature Testing**
   - Test if specific features are enabled for clients
   - Test with user IDs for percentage rollouts
   - Real-time validation

### 4. **Kill Switch**
   - Global toggle to revert ALL clients to baseline
   - Emergency feature disable
   - Visual status indicator

---

## 📋 Configuration

### Rulesets (`rulesets.yaml`)

Rulesets define **which features are available** for clients assigned to them.

```yaml
# Baseline - Core features for fallback
baseline:
  description: "Baseline feature set - core functionality only"
  features:
    - basic_dashboard
    - user_management
    - basic_reports
    - profile_settings

# Enterprise Tier - All features
enterprise_tier:
  description: "Enterprise tier with all features"
  baseline_ruleset: baseline  # Falls back to baseline on failure
  features:
    basic_dashboard: true
    enhanced_dashboard: true
    enterprise_dashboard: true
    user_management:
      enabled: true
      max_users: -1  # unlimited
    advanced_analytics: true
    sso_authentication: true
    api_access:
      enabled: true
      rate_limit: -1  # unlimited
    # ... 20+ more features
```

### Clients (`clients.yaml`)

Maps clients to their assigned rulesets. **Easy to modify!**

```yaml
acme_corp:
  ruleset: enterprise_tier  # Just change this to upgrade/downgrade
  metadata:
    name: "Acme Corporation"
    tier: "Enterprise"
    contact: "admin@acme.com"
    signup_date: "2024-01-15"

small_biz_llc:
  ruleset: free_tier  # Change to 'starter_tier' to upgrade
  metadata:
    name: "Small Biz LLC"
    tier: "Free"
    contact: "owner@smallbiz.com"
```

---

## 🔌 API Reference

### Get All Clients
```bash
GET /api/clients
```
Returns all clients with their rulesets and available features.

### Get Client Details
```bash
GET /api/client/<client_id>
```
Get detailed information about a specific client.

### Check Feature Access
```bash
GET /api/client/<client_id>/feature/<feature_name>?user_id=123
```
Check if a feature is enabled for a client (optionally with user context).

### Update Client Ruleset
```bash
PUT /api/client/<client_id>/ruleset
Body: { "ruleset": "professional_tier" }
```
Change a client's assigned ruleset.

### Create New Client
```bash
POST /api/client
Body: {
  "client_id": "new_client",
  "ruleset": "starter_tier",
  "metadata": { "name": "New Client Corp" }
}
```

### Toggle Kill Switch
```bash
POST /api/kill-switch
Body: { "activate": true }
```
Activate or deactivate the global kill switch.

### Get All Rulesets
```bash
GET /api/rulesets
```
Get all available rulesets with their features.

---

## 💡 Usage Examples

### Example 1: Basic Feature Check

```python
from feature_flag_client import FeatureFlagClient

client = FeatureFlagClient()

# Check if acme_corp has access to enterprise dashboard
if client.isEnabled("acme_corp", "enterprise_dashboard"):
    render_enterprise_dashboard()
else:
    render_basic_dashboard()  # Baseline fallback
```

### Example 2: Percentage Rollout

```python
# Beta tier has experimental_dashboard at 50% rollout
client = FeatureFlagClient()

# Check with user context for consistent hashing
if client.isEnabled("beta_tester_1", "experimental_dashboard", {"user_id": 42}):
    show_experimental_dashboard()  # User 42 gets new dashboard
else:
    show_standard_dashboard()      # User 42 gets old dashboard
```

### Example 3: Upgrading a Client

```python
client = FeatureFlagClient()

# Upgrade client from free to starter tier
client.update_client_ruleset("small_biz_llc", "starter_tier")

# Now they have access to starter tier features
print(client.get_client_features("small_biz_llc"))
# Output: {'basic_dashboard', 'enhanced_dashboard', 'advanced_reports', ...}
```

### Example 4: Emergency Kill Switch

```python
client = FeatureFlagClient()

# Activate kill switch - all clients revert to baseline
client.activate_kill_switch()

# Now ALL clients only have baseline features
print(client.isEnabled("acme_corp", "enterprise_dashboard"))  # False
print(client.isEnabled("acme_corp", "basic_dashboard"))       # True (baseline)

# Deactivate when issue is resolved
client.deactivate_kill_switch()
```

---

## 🧪 Testing

Run the comprehensive test suite:

```bash
python3 test_system.py
```

Tests include:
- ✅ Client and ruleset loading
- ✅ Feature access validation
- ✅ Baseline fallback
- ✅ Kill switch functionality
- ✅ Percentage rollouts (consistent hashing)
- ✅ Ruleset updates

All tests pass successfully!

---

## 🏗️ Architecture

### How It Works

1. **Clients are assigned to Rulesets**
   - Each client has ONE ruleset (e.g., `enterprise_tier`)
   - Rulesets define which features the client can access

2. **Rulesets have Baselines**
   - Each ruleset can specify a `baseline_ruleset`
   - If a feature fails or isn't available, fall back to baseline

3. **Kill Switch = Global Baseline**
   - When activated, ALL clients use ONLY baseline features
   - Emergency feature disable for system-wide issues

4. **Percentage Rollouts**
   - Features can have `percentage: 50` for gradual rollouts
   - Uses consistent hashing (user_id) for stable assignments

### Flow Diagram

```
Client Request → Is Kill Switch Active?
                 ├─ Yes → Use Baseline Features Only
                 └─ No  → Get Client's Ruleset
                          └─ Feature in Ruleset?
                             ├─ Yes → Check Percentage (if any)
                             │        └─ Pass → Feature Enabled
                             └─ No  → Check Baseline Ruleset
                                      └─ Feature Enabled/Disabled
```

---

## 📊 Available Rulesets

| Ruleset | Description | Features | Best For |
|---------|-------------|----------|----------|
| **baseline** | Core functionality only | 4 features | Fallback / Emergency |
| **free_tier** | Free/trial users | 5 features | Trial users |
| **starter_tier** | Entry-level paid | 9 features | Small businesses |
| **professional_tier** | Mid-tier clients | 14 features | Growing companies |
| **enterprise_tier** | Full-featured | 23 features | Enterprise clients |
| **beta_tier** | Experimental features | 15 features | Beta testers |
| **custom_tier** | Fully customizable | 14 features | Special agreements |

---

## 🔄 Adding New Features

### 1. Add feature to rulesets.yaml

```yaml
professional_tier:
  features:
    new_ai_feature:  # Add this
      enabled: true
      percentage: 25  # Optional: Gradual rollout
```

### 2. Use in your application

```python
if ff_client.isEnabled("client_id", "new_ai_feature"):
    show_ai_feature()
```

That's it! The feature is now available to all clients in `professional_tier`.

---

## 🛡️ Baseline Fallback Strategy

**Why Baselines Matter:**

When a new feature fails or causes issues, clients automatically fall back to their baseline features. This ensures:

- ✅ **No complete outages** - Core features always work
- ✅ **Graceful degradation** - Users see reduced functionality, not errors
- ✅ **Quick recovery** - Activate kill switch to revert everyone

**Example Scenario:**

1. `enterprise_tier` has 23 features
2. New feature `predictive_analytics` causes crashes
3. Activate kill switch → All clients use `baseline` (4 core features)
4. Fix the issue
5. Deactivate kill switch → Clients return to full feature sets

---

## 🚦 Kill Switch Use Cases

1. **Emergency Bug** - New feature causing crashes → Activate kill switch
2. **Database Issues** - Advanced features need DB → Disable, keep baseline working
3. **API Downtime** - Third-party API down → Disable dependent features
4. **Planned Maintenance** - Temporarily reduce to core features

---

## 📝 Configuration Best Practices

### 1. **Keep Baseline Small**
   - Only essential features users MUST have
   - Dashboard, auth, basic functionality

### 2. **Clear Tier Progression**
   - Free → Starter → Professional → Enterprise
   - Each tier builds on the previous one

### 3. **Test in Beta First**
   - Use `beta_tier` with percentage rollouts
   - Validate before promoting to production tiers

### 4. **Easy Client Upgrades**
   - Just change `ruleset:` in `clients.yaml`
   - Or use dashboard / API

---

## 🎉 Summary

You now have a **fully functional feature flagging system** with:

✅ Client-based feature access  
✅ Ruleset management (tiers/plans)  
✅ Baseline fallback for safety  
✅ Kill switch for emergencies  
✅ Web dashboard for management  
✅ REST API for integration  
✅ Percentage rollouts  
✅ Easy configuration via YAML  

**Start the dashboard with `python3 app.py` and visit http://localhost:5000!**
