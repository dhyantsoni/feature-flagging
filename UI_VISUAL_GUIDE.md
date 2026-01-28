# Feature Flag Dashboard - Visual Guide

## UI Layout (After Loading)

```
┌─────────────────────────────────────────────────────────────────┐
│  🚩 Feature Flag Management Dashboard                           │
│  [Project Selector ▼] [+ New Project]  ☐ Kill Switch: OFF      │
└─────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────┬──────────────────────────────┐
│ SIDEBAR                          │ MAIN CONTENT                 │
│                                  │                              │
│ Clients                          │ Client Details               │
│ [Search... ]                     │ ═════════════════════════════ │
│                                  │                              │
│ ✓ Acme Corporation               │ Name: Acme Corporation       │
│   Enterprise (23 features)       │ Tier: Enterprise             │
│                                  │ Ruleset: enterprise_tier     │
│ ✓ Beta Tester Company            │ Status: Active ●             │
│   Beta (15 features)             │                              │
│                                  │ [Change Ruleset] [Test Feat] │
│ ✓ Freelance User                 │ ════════════════════════════ │
│   Free (5 features)              │                              │
│                                  │ Available Features:          │
│ ✓ Global Enterprises             │ ✓ export_data                │
│   Enterprise (23 features)       │ ✓ user_management            │
│                                  │ ✓ dedicated_support          │
│ ✓ Mid-Sized Company              │ ✓ real_time_reports          │
│   Professional (14 features)     │ ✓ ... (23 total)             │
│                                  │                              │
│ ✓ Small Biz LLC                  │                              │
│   Free (5 features)              │                              │
│                                  │                              │
│ ✓ Startup Co                     │                              │
│   Professional (14 features)     │                              │
│                                  │                              │
│ ✓ TechStart Inc                  │                              │
│   Starter (9 features)           │                              │
│                                  │                              │
│ [+ Add New Client]               │                              │
│                                  │                              │
└──────────────────────────────────┴──────────────────────────────┘
```

## Interactive Elements

### Button Actions

1. **Change Ruleset Button**
   - Shows modal with ruleset dropdown
   - Lets you change the client's ruleset
   - Updates immediately upon save

2. **Test Feature Button**
   - Shows form to test a feature
   - Enter feature name and optional user ID
   - Shows result: "Enabled ✓" or "Disabled ✗"

3. **Add New Client Button**
   - Shows form to create new client
   - Fields: Client ID, Name, Ruleset, Contact Email
   - Adds client to the system

4. **Kill Switch Toggle**
   - Top right checkbox
   - Controls global feature flag shutdown
   - Shows "ON" or "OFF" status

5. **Search Box**
   - Filters clients by name or ID in real-time
   - Case-insensitive

### Modals

All modals have close button (✕) in top right corner.

#### Change Ruleset Modal
```
╔═══════════════════════════════════╗
║ Change Ruleset                    ║  ✕
║═════════════════════════════════════
║ Select a new ruleset for Acme Corporation:
║ [Select: enterprise_tier ▼        ]
║                                    
║ [Update Ruleset] [Cancel]          
╚═══════════════════════════════════╝
```

#### Test Feature Modal
```
╔═══════════════════════════════════╗
║ Test Feature Access               ║  ✕
║═════════════════════════════════════
║ Feature Name: [________________]   
║ User ID:      [________________]   
║ (optional, for percentage rollouts)
║                                    
║ [Test Feature] [Cancel]            
║                                    
║ Test Result for export_data        
║ Enabled: YES ✓                     
║ Reason: Client tier allows access  
╚═══════════════════════════════════╝
```

#### Add New Client Modal
```
╔═══════════════════════════════════╗
║ Add New Client                    ║  ✕
║═════════════════════════════════════
║ Client ID:     [________________]  
║ Client Name:   [________________]  
║ Ruleset:       [Select ▼       ]   
║ Contact Email: [________________]  
║                                    
║ [Create Client] [Cancel]           
╚═══════════════════════════════════╝
```

## Color Scheme

- **Background**: Dark blue-gray (#0f172a)
- **Surfaces**: Slightly lighter (#1e293b)
- **Primary Color**: Indigo (#6366f1)
- **Success**: Green (#22c55e)
- **Danger/Error**: Red (#ef4444)
- **Text Primary**: Light gray (#f1f5f9)
- **Text Secondary**: Muted gray (#94a3b8)

## Features Visible by Default

Welcome Message (until you select a client):
```
Welcome to Feature Flag Management

Select a client from the list to view their features and manage their ruleset.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  8                  7              Inactive
  Total Clients      Rulesets       Kill Switch
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

## Troubleshooting

### If you can't see the UI:

1. **Check if page loaded** - Should see "🚩 Feature Flag Management Dashboard" at the top
2. **Check CSS loaded** - Open DevTools (F12) → Network tab → should see `style.css` (200 OK)
3. **Check for errors** - DevTools → Console tab → should be no red errors
4. **Refresh page** - Try Ctrl+F5 (hard refresh)
5. **Try different browser** - Make sure it's not a browser cache issue

### If buttons don't work:

1. Make sure JavaScript loaded - Network tab should show `dashboard.js` (200 OK)
2. Check Console for errors (F12 → Console)
3. Try clicking on a client first - some buttons require a client selected
4. Check that you're on the latest deployment URL

### If modals don't appear:

1. Check z-index in DevTools - modals should appear on top
2. Try closing any other open modals first
3. Check console for JavaScript errors
