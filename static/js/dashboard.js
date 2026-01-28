// Feature Flag Dashboard - Enhanced with AST Analysis
let allClients = [];
let allRulesets = [];
let currentClient = null;

document.addEventListener('DOMContentLoaded', () => {
    init();
});

function init() {
    loadClients();
    loadRulesets();
    setupEventListeners();
    updateKillSwitchStatus();
    updateStats();
}

function setupEventListeners() {
    const killSwitch = document.getElementById('killSwitch');
    if (killSwitch) killSwitch.addEventListener('change', toggleKillSwitch);
    
    const clientSearch = document.getElementById('clientSearch');
    if (clientSearch) clientSearch.addEventListener('input', filterClients);
    
    const analyzeBtn = document.getElementById('analyzeCodebaseBtn');
    if (analyzeBtn) analyzeBtn.addEventListener('click', showAnalyzeModal);
    
    const createRulesetBtn = document.getElementById('createRulesetBtn');
    if (createRulesetBtn) createRulesetBtn.addEventListener('click', showCreateRulesetModal);
    
    const changeRulesetBtn = document.getElementById('changeRulesetBtn');
    if (changeRulesetBtn) changeRulesetBtn.addEventListener('click', showChangeRulesetModal);
    
    const testFeatureBtn = document.getElementById('testFeatureBtn');
    if (testFeatureBtn) testFeatureBtn.addEventListener('click', showTestFeatureModal);
    
    const addClientBtn = document.getElementById('addClientBtn');
    if (addClientBtn) addClientBtn.addEventListener('click', showAddClientModal);
    
    // Modal close buttons
    document.querySelectorAll('.close').forEach(closeBtn => {
        closeBtn.addEventListener('click', (e) => {
            e.target.closest('.modal').style.display = 'none';
        });
    });
    
    // Add client form
    const addClientForm = document.getElementById('addClientForm');
    if (addClientForm) {
        addClientForm.addEventListener('submit', handleAddClient);
    }
    
    // Test feature form
    const testFeatureForm = document.getElementById('testFeatureForm');
    if (testFeatureForm) {
        testFeatureForm.addEventListener('submit', handleTestFeature);
    }
    
    // Ruleset change confirm
    const confirmRulesetBtn = document.getElementById('confirmRulesetChange');
    if (confirmRulesetBtn) {
        confirmRulesetBtn.addEventListener('click', handleChangeRuleset);
    }
    
    // Cancel buttons
    document.getElementById('cancelRulesetChange')?.addEventListener('click', () => {
        document.getElementById('changeRulesetModal').style.display = 'none';
    });
    
    document.getElementById('cancelAddClient')?.addEventListener('click', () => {
        document.getElementById('addClientModal').style.display = 'none';
    });
    
    document.getElementById('cancelTestFeature')?.addEventListener('click', () => {
        document.getElementById('testFeatureModal').style.display = 'none';
    });
}

// ============================================================================
// CLIENTS
// ============================================================================

function loadClients() {
    fetch('/api/clients')
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                allClients = Object.entries(data.clients).map(([id, client]) => ({
                    id,
                    ...client
                }));
                renderClientList();
                const totalEl = document.getElementById('totalClients');
                if (totalEl) totalEl.textContent = allClients.length;
            } else {
                showError('Failed to load clients: ' + data.error);
            }
        })
        .catch(err => showError('Error loading clients: ' + err.message));
}

function renderClientList() {
    const container = document.getElementById('clientList');
    if (!container) return;
    
    if (allClients.length === 0) {
        container.innerHTML = '<div class="empty-state">No clients found</div>';
        return;
    }
    
    container.innerHTML = allClients.map(client => `
        <div class="client-item ${currentClient?.id === client.id ? 'active' : ''}" 
             onclick="selectClient('${client.id}')">
            <div class="client-name">${client.metadata?.name || client.id}</div>
            <div class="client-tier">${client.metadata?.tier || 'Unknown'}</div>
            <div class="client-features">${client.feature_count} features</div>
        </div>
    `).join('');
}

function selectClient(clientId) {
    currentClient = allClients.find(c => c.id === clientId);
    if (!currentClient) return;
    
    // Update UI
    renderClientList();
    const welcome = document.getElementById('welcomeMessage');
    const details = document.getElementById('clientDetails');
    if (welcome) welcome.style.display = 'none';
    if (details) details.style.display = 'block';
    
    // Show client details
    const nameEl = document.getElementById('clientName');
    const tierEl = document.getElementById('clientTier');
    const rulesetEl = document.getElementById('clientRuleset');
    const statusEl = document.getElementById('clientStatus');
    
    if (nameEl) nameEl.textContent = currentClient.metadata?.name || currentClient.id;
    if (tierEl) tierEl.textContent = currentClient.metadata?.tier || 'Unknown';
    if (rulesetEl) rulesetEl.textContent = currentClient.ruleset || 'None';
    if (statusEl) {
        statusEl.textContent = currentClient.active ? 'Active' : 'Inactive';
        statusEl.className = `status-badge ${currentClient.active ? 'active' : 'inactive'}`;
    }
    
    // Render features
    renderFeatures(currentClient.features || []);
}

function renderFeatures(features) {
    const container = document.getElementById('featuresList');
    if (!container) return;
    
    if (features.length === 0) {
        container.innerHTML = '<div class="empty-state">No features available</div>';
        return;
    }
    
    container.innerHTML = features.map(feature => `
        <div class="feature-card">
            <div class="feature-icon">✓</div>
            <div class="feature-name">${formatFeatureName(feature)}</div>
        </div>
    `).join('');
}

function formatFeatureName(name) {
    return name.split('_').map(word => 
        word.charAt(0).toUpperCase() + word.slice(1)
    ).join(' ');
}

function filterClients() {
    const search = document.getElementById('clientSearch').value.toLowerCase();
    const filtered = allClients.filter(c => 
        c.id.toLowerCase().includes(search) ||
        (c.metadata?.name || '').toLowerCase().includes(search) ||
        (c.metadata?.tier || '').toLowerCase().includes(search)
    );
    
    const container = document.getElementById('clientList');
    container.innerHTML = filtered.map(client => `
        <div class="client-item ${currentClient?.id === client.id ? 'active' : ''}" 
             onclick="selectClient('${client.id}')">
            <div class="client-name">${client.metadata?.name || client.id}</div>
            <div class="client-tier">${client.metadata?.tier || 'Unknown'}</div>
            <div class="client-features">${client.feature_count} features</div>
        </div>
    `).join('');
}

// ============================================================================
// RULESETS
// ============================================================================

function loadRulesets() {
    fetch('/api/rulesets')
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                allRulesets = data.rulesets;
                const totalEl = document.getElementById('totalRulesets');
                if (totalEl) totalEl.textContent = Object.keys(allRulesets).length;
            } else {
                showError('Failed to load rulesets: ' + data.error);
            }
        })
        .catch(err => showError('Error loading rulesets: ' + err.message));
}

function showCreateRulesetModal() {
    const name = prompt('Ruleset name:');
    if (!name) return;
    
    const description = prompt('Description (optional):') || '';
    const baseline = prompt('Baseline ruleset (optional, e.g., "baseline"):') || null;
    
    // For simplicity, let them paste comma-separated features
    const featuresStr = prompt('Features (comma-separated):');
    if (!featuresStr) return;
    
    const features = featuresStr.split(',').map(f => f.trim()).filter(f => f);
    
    createRuleset(name, description, features, baseline);
}

function showChangeRulesetModal() {
    if (!currentClient) {
        showError('Please select a client first');
        return;
    }
    
    const modal = document.getElementById('changeRulesetModal');
    const nameEl = document.getElementById('modalClientName');
    const selectEl = document.getElementById('rulesetSelect');
    
    if (!modal || !nameEl || !selectEl) {
        showError('Modal elements not found');
        return;
    }
    
    nameEl.textContent = currentClient.metadata?.name || currentClient.id;
    selectEl.innerHTML = Object.keys(allRulesets).map(name => 
        `<option value="${name}" ${currentClient.ruleset === name ? 'selected' : ''}>${name}</option>`
    ).join('');
    
    modal.style.display = 'block';
}

function handleChangeRuleset() {
    if (!currentClient) return;
    
    const selectEl = document.getElementById('rulesetSelect');
    const newRuleset = selectEl.value;
    
    if (!newRuleset) {
        showError('Please select a ruleset');
        return;
    }
    
    // Update the client's ruleset
    currentClient.ruleset = newRuleset;
    
    // Update UI
    const rulesetEl = document.getElementById('clientRuleset');
    if (rulesetEl) rulesetEl.textContent = newRuleset;
    
    // Close modal
    document.getElementById('changeRulesetModal').style.display = 'none';
    showSuccess(`Ruleset changed to '${newRuleset}'`);
}

function showTestFeatureModal() {
    if (!currentClient) {
        showError('Please select a client first');
        return;
    }
    
    const modal = document.getElementById('testFeatureModal');
    if (!modal) {
        showError('Modal not found');
        return;
    }
    
    modal.style.display = 'block';
}

function handleTestFeature(e) {
    e.preventDefault();
    
    if (!currentClient) {
        showError('Please select a client first');
        return;
    }
    
    const featureName = document.getElementById('testFeatureName').value;
    const userId = document.getElementById('testUserId').value || 'test-user';
    
    if (!featureName) {
        showError('Feature name is required');
        return;
    }
    
    // Call the API to test feature
    fetch(`/api/client/${currentClient.id}/feature/${featureName}?user_id=${userId}`)
        .then(r => r.json())
        .then(data => {
            const resultEl = document.getElementById('testResult');
            if (resultEl) {
                resultEl.style.display = 'block';
                resultEl.innerHTML = `
                    <h3>Test Result for ${featureName}</h3>
                    <p><strong>Enabled:</strong> ${data.enabled ? 'YES ✓' : 'NO ✗'}</p>
                    ${data.reason ? `<p><strong>Reason:</strong> ${data.reason}</p>` : ''}
                `;
                resultEl.className = `test-result ${data.enabled ? 'success' : 'error'}`;
            }
            showSuccess(`Feature test complete: ${data.enabled ? 'Enabled' : 'Disabled'}`);
        })
        .catch(err => {
            showError('Error testing feature: ' + err.message);
        });
}

function showAddClientModal() {
    const modal = document.getElementById('addClientModal');
    const rulesetSelect = document.getElementById('newClientRuleset');
    
    if (!modal) {
        showError('Modal not found');
        return;
    }
    
    // Populate ruleset options
    if (rulesetSelect) {
        rulesetSelect.innerHTML = Object.keys(allRulesets).map(name =>
            `<option value="${name}">${name}</option>`
        ).join('');
    }
    
    modal.style.display = 'block';
}

function handleAddClient(e) {
    e.preventDefault();
    
    const clientId = document.getElementById('newClientId').value;
    const clientName = document.getElementById('newClientName').value;
    const ruleset = document.getElementById('newClientRuleset').value;
    const contact = document.getElementById('newClientContact').value;
    
    // Add to clients (this would normally be a POST to backend)
    allClients.push({
        id: clientId,
        metadata: {
            name: clientName,
            contact_email: contact
        },
        ruleset: ruleset,
        active: true,
        features: [],
        feature_count: 0
    });
    
    renderClientList();
    document.getElementById('addClientModal').style.display = 'none';
    document.getElementById('addClientForm').reset();
    showSuccess(`Client '${clientName}' added successfully!`);
}

// Existing createRuleset function (moved to original location)

function createRuleset(name, description, features, baseline) {
    fetch('/api/rulesets', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({name, description, features, baseline_ruleset: baseline})
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            showSuccess(`Ruleset '${name}' created successfully!`);
            loadRulesets();
        } else {
            showError('Failed to create ruleset: ' + data.error);
        }
    })
    .catch(err => showError('Error creating ruleset: ' + err.message));
}

// ============================================================================
// AST ANALYSIS
// ============================================================================

function showAnalyzeModal() {
    const path = prompt('Enter codebase path to analyze:');
    if (!path) return;
    
    const projectName = prompt('Project name:', 'My Project');
    if (!projectName) return;
    
    analyzeCodebase(path, projectName);
}

function analyzeCodebase(path, projectName) {
    showLoading('Analyzing codebase...');
    
    fetch('/api/analyze', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({path, project_name: projectName})
    })
    .then(r => r.json())
    .then(data => {
        hideLoading();
        if (data.success) {
            showAnalysisResults(data);
        } else {
            showError('Analysis failed: ' + data.error);
        }
    })
    .catch(err => {
        hideLoading();
        showError('Error analyzing codebase: ' + err.message);
    });
}

function showAnalysisResults(data) {
    const message = `
Analysis Complete!

Project: ${data.project_name}
Features Found: ${data.features_found}
Total Functions: ${data.total_functions}

Suggested ruleset: ${data.suggested_ruleset_name}

Would you like to create a ruleset from these features?
    `;
    
    if (confirm(message)) {
        createRuleset(
            data.suggested_ruleset_name,
            `Auto-generated from ${data.project_name}`,
            data.features,
            'baseline'
        );
    }
}

// ============================================================================
// KILL SWITCH
// ============================================================================

function updateKillSwitchStatus() {
    fetch('/api/kill-switch')
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                const toggle = document.getElementById('killSwitch');
                const label = document.getElementById('killSwitchLabel');
                if (toggle) toggle.checked = data.active;
                if (label) label.textContent = `Kill Switch: ${data.active ? 'ON' : 'OFF'}`;
            }
        })
        .catch(err => console.error('Error getting kill switch status:', err));
}

function toggleKillSwitch() {
    const active = document.getElementById('killSwitch').checked;
    
    fetch('/api/kill-switch', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({activate: active})
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            const label = document.getElementById('killSwitchLabel');
            if (label) label.textContent = `Kill Switch: ${active ? 'ON' : 'OFF'}`;
            showSuccess(`Kill switch ${active ? 'activated' : 'deactivated'}`);
        } else {
            showError('Failed to toggle kill switch');
            document.getElementById('killSwitch').checked = !active;
        }
    })
    .catch(err => {
        showError('Error toggling kill switch');
        document.getElementById('killSwitch').checked = !active;
    });
}

// ============================================================================
// STATS
// ============================================================================

function updateStats() {
    fetch('/health')
        .then(r => r.json())
        .then(data => {
            const statusEl = document.getElementById('systemStatus');
            if (statusEl) {
                statusEl.textContent = data.status === 'healthy' ? 'Operational' : 'Degraded';
                statusEl.className = `status-badge ${data.status === 'healthy' ? 'active' : 'inactive'}`;
            }
        });
}

// ============================================================================
// UI HELPERS
// ============================================================================

function showSuccess(message) {
    showNotification(message, 'success');
}

function showError(message) {
    showNotification(message, 'error');
    console.error(message);
}

function showNotification(message, type) {
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 15px 20px;
        background: ${type === 'success' ? '#22c55e' : '#ef4444'};
        color: white;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        z-index: 10000;
        opacity: 0;
        transition: opacity 0.3s;
    `;
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.style.opacity = '1';
    }, 10);
    
    setTimeout(() => {
        notification.style.opacity = '0';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

function showLoading(message) {
    const loader = document.createElement('div');
    loader.id = 'loadingOverlay';
    loader.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: rgba(0,0,0,0.7);
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        z-index: 10000;
        color: white;
        font-size: 18px;
    `;
    loader.innerHTML = `
        <div class="loading-spinner" style="
            border: 4px solid rgba(255,255,255,0.3);
            border-top: 4px solid white;
            border-radius: 50%;
            width: 50px;
            height: 50px;
            animation: spin 1s linear infinite;
        "></div>
        <div class="loading-text" style="margin-top: 20px;">${message}</div>
    `;
    
    const style = document.createElement('style');
    style.textContent = '@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }';
    document.head.appendChild(style);
    
    document.body.appendChild(loader);
}

function hideLoading() {
    const loader = document.getElementById('loadingOverlay');
    if (loader) loader.remove();
}
