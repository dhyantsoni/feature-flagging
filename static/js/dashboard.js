// Feature Flag Dashboard - Enhanced v2.1
// Includes: Targeting Rules, Scheduling, Audit Logs, API Keys

let allClients = [];
let allRulesets = [];
let currentClient = null;
let targetingRules = [];
let schedules = [];
let auditLogs = [];
let apiKeys = [];

document.addEventListener('DOMContentLoaded', () => {
    init();
});

function init() {
    loadClients();
    loadRulesets();
    setupEventListeners();
    updateKillSwitchStatus();
    loadSystemStatus();

    // Initialize nixo if available
    if (typeof initNixo === 'function') {
        initNixo();
    }
}

function setupEventListeners() {
    // Tab navigation
    document.querySelectorAll('.nav-btn').forEach(btn => {
        btn.addEventListener('click', (e) => switchTab(e.target.dataset.tab));
    });

    // Kill switch
    const killSwitch = document.getElementById('killSwitch');
    if (killSwitch) killSwitch.addEventListener('change', toggleKillSwitch);

    // Client search
    const clientSearch = document.getElementById('clientSearch');
    if (clientSearch) clientSearch.addEventListener('input', filterClients);

    // Client management buttons
    document.getElementById('changeRulesetBtn')?.addEventListener('click', showChangeRulesetModal);
    document.getElementById('testFeatureBtn')?.addEventListener('click', showTestFeatureModal);
    document.getElementById('addClientBtn')?.addEventListener('click', showAddClientModal);

    // Targeting rules
    document.getElementById('addTargetingRuleBtn')?.addEventListener('click', showAddTargetingRuleModal);
    document.getElementById('targetingSearch')?.addEventListener('input', filterTargetingRules);
    document.getElementById('addConditionBtn')?.addEventListener('click', addConditionRow);

    // Schedules
    document.getElementById('addScheduleBtn')?.addEventListener('click', showAddScheduleModal);
    document.getElementById('scheduleType')?.addEventListener('change', toggleScheduleFields);

    // Audit logs
    document.getElementById('refreshAuditBtn')?.addEventListener('click', loadAuditLogs);
    document.getElementById('auditEntityFilter')?.addEventListener('change', loadAuditLogs);

    // API Keys
    document.getElementById('createApiKeyBtn')?.addEventListener('click', showCreateApiKeyModal);
    document.getElementById('copyApiKey')?.addEventListener('click', copyApiKey);

    // Modal close buttons
    document.querySelectorAll('.close').forEach(closeBtn => {
        closeBtn.addEventListener('click', (e) => {
            e.target.closest('.modal').style.display = 'none';
        });
    });

    // Form submissions
    document.getElementById('addClientForm')?.addEventListener('submit', handleAddClient);
    document.getElementById('testFeatureForm')?.addEventListener('submit', handleTestFeature);
    document.getElementById('addTargetingRuleForm')?.addEventListener('submit', handleAddTargetingRule);
    document.getElementById('addScheduleForm')?.addEventListener('submit', handleAddSchedule);
    document.getElementById('createApiKeyForm')?.addEventListener('submit', handleCreateApiKey);

    // Confirm/cancel buttons
    document.getElementById('confirmRulesetChange')?.addEventListener('click', handleChangeRuleset);
    document.getElementById('cancelRulesetChange')?.addEventListener('click', () => closeModal('changeRulesetModal'));
    document.getElementById('cancelAddClient')?.addEventListener('click', () => closeModal('addClientModal'));
    document.getElementById('cancelTestFeature')?.addEventListener('click', () => closeModal('testFeatureModal'));
    document.getElementById('cancelAddTargetingRule')?.addEventListener('click', () => closeModal('addTargetingRuleModal'));
    document.getElementById('cancelAddSchedule')?.addEventListener('click', () => closeModal('addScheduleModal'));
    document.getElementById('cancelCreateApiKey')?.addEventListener('click', () => closeModal('createApiKeyModal'));

    // Click outside modal to close
    window.addEventListener('click', (e) => {
        if (e.target.classList.contains('modal')) {
            e.target.style.display = 'none';
        }
    });
}

// ============================================================================
// TAB NAVIGATION
// ============================================================================

function switchTab(tabName) {
    // Update nav buttons
    document.querySelectorAll('.nav-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.tab === tabName);
    });

    // Update tab content
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.remove('active');
    });

    const tabContent = document.getElementById(`${tabName}Tab`);
    if (tabContent) {
        tabContent.classList.add('active');
    }

    // Load data for the tab
    switch (tabName) {
        case 'targeting':
            loadTargetingRules();
            break;
        case 'schedules':
            loadSchedules();
            break;
        case 'audit':
            loadAuditLogs();
            break;
        case 'api-keys':
            loadApiKeys();
            break;
        // Nixo tabs
        case 'nixo-features':
            if (typeof loadNixoFeatures === 'function') loadNixoFeatures();
            break;
        case 'nixo-rulesets':
            if (typeof loadNixoRulesets === 'function') loadNixoRulesets();
            break;
        case 'nixo-clients':
            if (typeof loadNixoClients === 'function') loadNixoClients();
            break;
    }
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
                document.getElementById('totalClients').textContent = allClients.length;
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

    renderClientList();
    document.getElementById('welcomeMessage').style.display = 'none';
    document.getElementById('clientDetails').style.display = 'block';

    document.getElementById('clientName').textContent = currentClient.metadata?.name || currentClient.id;
    document.getElementById('clientId').textContent = currentClient.id;
    document.getElementById('clientTier').textContent = currentClient.metadata?.tier || 'Unknown';
    document.getElementById('currentRuleset').textContent = currentClient.ruleset || 'None';
    document.getElementById('clientContact').textContent = currentClient.metadata?.contact || '-';
    document.getElementById('clientSignupDate').textContent = currentClient.metadata?.signup_date || '-';
    document.getElementById('featureCount').textContent = currentClient.feature_count || 0;

    // Get ruleset description
    const ruleset = allRulesets[currentClient.ruleset];
    document.getElementById('rulesetDescription').textContent = ruleset?.description || '-';

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
                document.getElementById('totalRulesets').textContent = Object.keys(allRulesets).length;
            }
        })
        .catch(err => showError('Error loading rulesets: ' + err.message));
}

function showChangeRulesetModal() {
    if (!currentClient) {
        showError('Please select a client first');
        return;
    }

    const modal = document.getElementById('changeRulesetModal');
    document.getElementById('modalClientName').textContent = currentClient.metadata?.name || currentClient.id;

    const selectEl = document.getElementById('rulesetSelect');
    selectEl.innerHTML = Object.keys(allRulesets).map(name =>
        `<option value="${name}" ${currentClient.ruleset === name ? 'selected' : ''}>${name}</option>`
    ).join('');

    modal.style.display = 'block';
}

function handleChangeRuleset() {
    if (!currentClient) return;

    const newRuleset = document.getElementById('rulesetSelect').value;
    if (!newRuleset) return;

    fetch(`/api/clients/${currentClient.id}/ruleset`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ruleset: newRuleset })
    })
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                currentClient.ruleset = newRuleset;
                document.getElementById('currentRuleset').textContent = newRuleset;
                closeModal('changeRulesetModal');
                showSuccess(`Ruleset changed to '${newRuleset}'`);
                loadClients();
            } else {
                showError('Failed to change ruleset: ' + data.error);
            }
        })
        .catch(err => showError('Error changing ruleset: ' + err.message));
}

// ============================================================================
// TEST FEATURE
// ============================================================================

function showTestFeatureModal() {
    if (!currentClient) {
        showError('Please select a client first');
        return;
    }
    document.getElementById('testResult').style.display = 'none';
    document.getElementById('testFeatureModal').style.display = 'block';
}

function handleTestFeature(e) {
    e.preventDefault();

    if (!currentClient) {
        showError('Please select a client first');
        return;
    }

    const featureName = document.getElementById('testFeatureName').value;
    const userId = document.getElementById('testUserId').value;
    const country = document.getElementById('testCountry').value;
    const detailed = document.getElementById('testDetailed').checked;

    let url = `/api/client/${currentClient.id}/feature/${featureName}`;
    if (detailed) {
        url += '/detailed';
    }

    const params = new URLSearchParams();
    if (userId) params.append('user_id', userId);
    if (country) params.append('country', country);
    if (params.toString()) url += '?' + params.toString();

    fetch(url)
        .then(r => r.json())
        .then(data => {
            const resultEl = document.getElementById('testResult');
            resultEl.style.display = 'block';

            if (detailed && data.success) {
                resultEl.innerHTML = `
                    <h3>Result: ${data.enabled ? 'ENABLED ✓' : 'DISABLED ✗'}</h3>
                    <p><strong>Source:</strong> ${data.source}</p>
                    <p><strong>Reason:</strong> ${data.reason}</p>
                    <p><strong>Ruleset:</strong> ${data.ruleset || 'N/A'}</p>
                    ${data.schedule ? `<p><strong>Schedule:</strong> ${JSON.stringify(data.schedule)}</p>` : ''}
                    ${data.targeting_rule ? `<p><strong>Targeting Rule:</strong> ${data.targeting_rule}</p>` : ''}
                `;
            } else {
                resultEl.innerHTML = `
                    <h3>Result: ${data.enabled ? 'ENABLED ✓' : 'DISABLED ✗'}</h3>
                `;
            }
            resultEl.className = `test-result ${data.enabled ? 'success' : 'error'}`;
        })
        .catch(err => showError('Error testing feature: ' + err.message));
}

// ============================================================================
// ADD CLIENT
// ============================================================================

function showAddClientModal() {
    const rulesetSelect = document.getElementById('newClientRuleset');
    rulesetSelect.innerHTML = Object.keys(allRulesets).map(name =>
        `<option value="${name}">${name}</option>`
    ).join('');
    document.getElementById('addClientModal').style.display = 'block';
}

function handleAddClient(e) {
    e.preventDefault();

    const clientId = document.getElementById('newClientId').value;
    const clientName = document.getElementById('newClientName').value;
    const ruleset = document.getElementById('newClientRuleset').value;
    const contact = document.getElementById('newClientContact').value;

    fetch('/api/clients', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            client_id: clientId,
            ruleset: ruleset,
            metadata: {
                name: clientName,
                contact: contact,
                signup_date: new Date().toISOString().split('T')[0]
            }
        })
    })
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                closeModal('addClientModal');
                document.getElementById('addClientForm').reset();
                showSuccess(`Client '${clientName}' created successfully!`);
                loadClients();
            } else {
                showError('Failed to create client: ' + data.error);
            }
        })
        .catch(err => showError('Error creating client: ' + err.message));
}

// ============================================================================
// TARGETING RULES
// ============================================================================

function loadTargetingRules() {
    const container = document.getElementById('targetingRulesList');
    container.innerHTML = '<div class="loading">Loading targeting rules...</div>';

    fetch('/api/targeting-rules')
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                targetingRules = data.rules || [];
                renderTargetingRules();
            } else {
                container.innerHTML = '<div class="empty-state">Could not load targeting rules</div>';
            }
        })
        .catch(err => {
            container.innerHTML = '<div class="empty-state">Targeting rules not available (requires Supabase)</div>';
        });
}

function renderTargetingRules() {
    const container = document.getElementById('targetingRulesList');

    if (targetingRules.length === 0) {
        container.innerHTML = '<div class="empty-state">No targeting rules defined. Create one to target features based on user attributes.</div>';
        return;
    }

    container.innerHTML = targetingRules.map(rule => `
        <div class="rule-card">
            <div class="rule-header">
                <h3>${rule.name}</h3>
                <span class="rule-action ${rule.action}">${rule.action.toUpperCase()}</span>
            </div>
            <div class="rule-details">
                <p><strong>Feature:</strong> ${rule.feature_name}</p>
                <p><strong>Priority:</strong> ${rule.priority}</p>
                <p><strong>Conditions:</strong></p>
                <ul>
                    ${(rule.conditions || []).map(c => `
                        <li>${c.attribute} ${c.operator} ${c.value || c.values?.join(', ')}</li>
                    `).join('')}
                </ul>
            </div>
            <div class="rule-actions">
                <button class="btn btn-sm" onclick="deleteTargetingRule('${rule.id}')">Delete</button>
            </div>
        </div>
    `).join('');
}

function filterTargetingRules() {
    const search = document.getElementById('targetingSearch').value.toLowerCase();
    const filtered = targetingRules.filter(r =>
        r.name.toLowerCase().includes(search) ||
        r.feature_name.toLowerCase().includes(search)
    );
    renderFilteredTargetingRules(filtered);
}

function renderFilteredTargetingRules(rules) {
    const container = document.getElementById('targetingRulesList');
    if (rules.length === 0) {
        container.innerHTML = '<div class="empty-state">No matching rules</div>';
        return;
    }
    // Same render logic as renderTargetingRules but with filtered data
    container.innerHTML = rules.map(rule => `
        <div class="rule-card">
            <div class="rule-header">
                <h3>${rule.name}</h3>
                <span class="rule-action ${rule.action}">${rule.action.toUpperCase()}</span>
            </div>
            <div class="rule-details">
                <p><strong>Feature:</strong> ${rule.feature_name}</p>
                <p><strong>Priority:</strong> ${rule.priority}</p>
            </div>
            <div class="rule-actions">
                <button class="btn btn-sm" onclick="deleteTargetingRule('${rule.id}')">Delete</button>
            </div>
        </div>
    `).join('');
}

function showAddTargetingRuleModal() {
    document.getElementById('addTargetingRuleModal').style.display = 'block';
}

function addConditionRow() {
    const container = document.getElementById('conditionsContainer');
    const row = document.createElement('div');
    row.className = 'condition-row';
    row.innerHTML = `
        <select class="condition-attr form-select">
            <option value="country">Country</option>
            <option value="device">Device</option>
            <option value="user_id">User ID</option>
            <option value="email">Email</option>
            <option value="plan">Plan</option>
            <option value="version">App Version</option>
        </select>
        <select class="condition-op form-select">
            <option value="equals">equals</option>
            <option value="not_equals">not equals</option>
            <option value="contains">contains</option>
            <option value="in">in list</option>
            <option value="not_in">not in list</option>
            <option value="gt">greater than</option>
            <option value="lt">less than</option>
            <option value="percentage">percentage</option>
        </select>
        <input type="text" class="condition-value form-input" placeholder="Value">
        <button type="button" class="btn btn-sm btn-danger remove-condition" onclick="this.parentElement.remove()">X</button>
    `;
    container.appendChild(row);
}

function handleAddTargetingRule(e) {
    e.preventDefault();

    const conditions = [];
    document.querySelectorAll('.condition-row').forEach(row => {
        const attr = row.querySelector('.condition-attr').value;
        const op = row.querySelector('.condition-op').value;
        const val = row.querySelector('.condition-value').value;

        if (val) {
            const condition = { attribute: attr, operator: op };
            if (op === 'in' || op === 'not_in') {
                condition.values = val.split(',').map(v => v.trim());
            } else {
                condition.value = val;
            }
            conditions.push(condition);
        }
    });

    const ruleData = {
        name: document.getElementById('targetingRuleName').value,
        feature_name: document.getElementById('targetingFeatureName').value,
        action: document.getElementById('targetingAction').value,
        priority: parseInt(document.getElementById('targetingPriority').value) || 0,
        conditions: conditions
    };

    fetch('/api/targeting-rules', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(ruleData)
    })
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                closeModal('addTargetingRuleModal');
                document.getElementById('addTargetingRuleForm').reset();
                showSuccess('Targeting rule created!');
                loadTargetingRules();
            } else {
                showError('Failed to create rule: ' + data.error);
            }
        })
        .catch(err => showError('Error creating rule: ' + err.message));
}

function deleteTargetingRule(ruleId) {
    if (!confirm('Delete this targeting rule?')) return;

    fetch(`/api/targeting-rules/${ruleId}`, { method: 'DELETE' })
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                showSuccess('Rule deleted');
                loadTargetingRules();
            } else {
                showError('Failed to delete rule');
            }
        });
}

// ============================================================================
// SCHEDULES
// ============================================================================

function loadSchedules() {
    const container = document.getElementById('schedulesList');
    container.innerHTML = '<div class="loading">Loading schedules...</div>';

    fetch('/api/schedules')
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                schedules = data.schedules || [];
                renderSchedules();
                loadUpcomingSchedules();
            } else {
                container.innerHTML = '<div class="empty-state">Could not load schedules</div>';
            }
        })
        .catch(() => {
            container.innerHTML = '<div class="empty-state">Schedules not available (requires Supabase)</div>';
        });
}

function renderSchedules() {
    const container = document.getElementById('schedulesList');

    if (schedules.length === 0) {
        container.innerHTML = '<div class="empty-state">No schedules defined. Create one to enable/disable features at specific times.</div>';
        return;
    }

    container.innerHTML = schedules.map(s => `
        <div class="schedule-card">
            <div class="schedule-header">
                <h3>${s.feature_name}</h3>
                <span class="schedule-type">${s.schedule_type}</span>
            </div>
            <div class="schedule-details">
                <p><strong>Action:</strong> ${s.enabled_during_schedule ? 'Enable' : 'Disable'}</p>
                ${s.start_at ? `<p><strong>Start:</strong> ${formatDate(s.start_at)}</p>` : ''}
                ${s.end_at ? `<p><strong>End:</strong> ${formatDate(s.end_at)}</p>` : ''}
                ${s.cron_expression ? `<p><strong>Cron:</strong> ${s.cron_expression}</p>` : ''}
                <p><strong>Priority:</strong> ${s.priority}</p>
                <p><strong>Active:</strong> ${s.is_active ? 'Yes' : 'No'}</p>
            </div>
            <div class="schedule-actions">
                <button class="btn btn-sm" onclick="deleteSchedule('${s.id}')">Delete</button>
            </div>
        </div>
    `).join('');
}

function loadUpcomingSchedules() {
    fetch('/api/schedules/upcoming?hours=24')
        .then(r => r.json())
        .then(data => {
            const container = document.getElementById('upcomingSchedules');
            if (data.success && data.schedules?.length > 0) {
                container.innerHTML = data.schedules.map(s => `
                    <div class="upcoming-item">
                        <strong>${s.feature_name}</strong> - ${formatDate(s.start_at)}
                    </div>
                `).join('');
            } else {
                container.innerHTML = '<div class="empty-state">No upcoming schedules</div>';
            }
        });
}

function showAddScheduleModal() {
    document.getElementById('addScheduleModal').style.display = 'block';
}

function toggleScheduleFields() {
    const type = document.getElementById('scheduleType').value;
    document.getElementById('dateRangeFields').style.display = type !== 'recurring' ? 'flex' : 'none';
    document.getElementById('cronField').style.display = type === 'recurring' ? 'block' : 'none';
}

function handleAddSchedule(e) {
    e.preventDefault();

    const scheduleData = {
        feature_name: document.getElementById('scheduleFeatureName').value,
        schedule_type: document.getElementById('scheduleType').value,
        enabled_during_schedule: document.getElementById('scheduleEnabled').value === 'true',
        priority: parseInt(document.getElementById('schedulePriority').value) || 0
    };

    const startAt = document.getElementById('scheduleStartAt').value;
    const endAt = document.getElementById('scheduleEndAt').value;
    const cron = document.getElementById('scheduleCron').value;

    if (startAt) scheduleData.start_at = new Date(startAt).toISOString();
    if (endAt) scheduleData.end_at = new Date(endAt).toISOString();
    if (cron) scheduleData.cron_expression = cron;

    fetch('/api/schedules', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(scheduleData)
    })
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                closeModal('addScheduleModal');
                document.getElementById('addScheduleForm').reset();
                showSuccess('Schedule created!');
                loadSchedules();
            } else {
                showError('Failed to create schedule: ' + data.error);
            }
        })
        .catch(err => showError('Error creating schedule: ' + err.message));
}

function deleteSchedule(scheduleId) {
    if (!confirm('Delete this schedule?')) return;

    fetch(`/api/schedules/${scheduleId}`, { method: 'DELETE' })
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                showSuccess('Schedule deleted');
                loadSchedules();
            } else {
                showError('Failed to delete schedule');
            }
        });
}

// ============================================================================
// AUDIT LOGS
// ============================================================================

function loadAuditLogs() {
    const container = document.getElementById('auditLogList');
    container.innerHTML = '<div class="loading">Loading audit logs...</div>';

    const entityType = document.getElementById('auditEntityFilter')?.value || '';
    let url = '/api/audit-logs/recent?hours=168'; // Last week
    if (entityType) {
        url = `/api/audit-logs?entity_type=${entityType}&limit=100`;
    }

    fetch(url)
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                auditLogs = data.logs || [];
                renderAuditLogs();
            } else {
                container.innerHTML = '<div class="empty-state">Could not load audit logs</div>';
            }
        })
        .catch(() => {
            container.innerHTML = '<div class="empty-state">Audit logs not available (requires Supabase)</div>';
        });
}

function renderAuditLogs() {
    const container = document.getElementById('auditLogList');

    if (auditLogs.length === 0) {
        container.innerHTML = '<div class="empty-state">No audit logs found</div>';
        return;
    }

    container.innerHTML = `
        <table class="audit-table">
            <thead>
                <tr>
                    <th>Time</th>
                    <th>Action</th>
                    <th>Entity</th>
                    <th>Actor</th>
                    <th>Changes</th>
                </tr>
            </thead>
            <tbody>
                ${auditLogs.map(log => `
                    <tr>
                        <td>${formatDate(log.timestamp)}</td>
                        <td><span class="action-badge ${log.action}">${log.action}</span></td>
                        <td>${log.entity_type}: ${log.entity_name || log.entity_id || '-'}</td>
                        <td>${log.actor_name || log.actor_id || 'System'}</td>
                        <td>${formatChanges(log.changes)}</td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
    `;
}

function formatChanges(changes) {
    if (!changes) return '-';
    if (changes.after && !changes.before) return 'Created';
    if (changes.before && !changes.after) return 'Deleted';
    if (changes.before && changes.after) {
        const keys = Object.keys(changes.after);
        return keys.slice(0, 2).map(k => `${k}: ${changes.after[k]}`).join(', ');
    }
    return '-';
}

// ============================================================================
// API KEYS
// ============================================================================

function loadApiKeys() {
    const container = document.getElementById('apiKeysList');
    container.innerHTML = '<div class="loading">Loading API keys...</div>';

    fetch('/api/keys')
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                apiKeys = data.keys || [];
                renderApiKeys();
            } else {
                container.innerHTML = '<div class="empty-state">Could not load API keys</div>';
            }
        })
        .catch(() => {
            container.innerHTML = '<div class="empty-state">API keys not available (requires Supabase)</div>';
        });
}

function renderApiKeys() {
    const container = document.getElementById('apiKeysList');

    if (apiKeys.length === 0) {
        container.innerHTML = '<div class="empty-state">No API keys. Create one for programmatic access.</div>';
        return;
    }

    container.innerHTML = apiKeys.map(key => `
        <div class="api-key-card ${key.is_active ? '' : 'inactive'}">
            <div class="key-header">
                <h3>${key.name}</h3>
                <code>${key.key_prefix}...</code>
            </div>
            <div class="key-details">
                <p><strong>Permissions:</strong> ${(key.permissions || []).join(', ')}</p>
                <p><strong>Rate Limit:</strong> ${key.rate_limit}/hour</p>
                <p><strong>Created:</strong> ${formatDate(key.created_at)}</p>
                ${key.last_used_at ? `<p><strong>Last Used:</strong> ${formatDate(key.last_used_at)}</p>` : ''}
                ${key.expires_at ? `<p><strong>Expires:</strong> ${formatDate(key.expires_at)}</p>` : ''}
                <p><strong>Status:</strong> ${key.is_active ? 'Active' : 'Revoked'}</p>
            </div>
            ${key.is_active ? `
                <div class="key-actions">
                    <button class="btn btn-sm btn-danger" onclick="revokeApiKey('${key.id}')">Revoke</button>
                </div>
            ` : ''}
        </div>
    `).join('');
}

function showCreateApiKeyModal() {
    document.getElementById('newApiKeyResult').style.display = 'none';
    document.getElementById('createApiKeyForm').style.display = 'block';
    document.getElementById('createApiKeyModal').style.display = 'block';
}

function handleCreateApiKey(e) {
    e.preventDefault();

    const permissions = Array.from(document.getElementById('apiKeyPermissions').selectedOptions)
        .map(opt => opt.value);

    const keyData = {
        name: document.getElementById('apiKeyName').value,
        description: document.getElementById('apiKeyDescription').value,
        permissions: permissions,
        rate_limit: parseInt(document.getElementById('apiKeyRateLimit').value) || 1000
    };

    const expiresIn = document.getElementById('apiKeyExpires').value;
    if (expiresIn) {
        keyData.expires_in_days = parseInt(expiresIn);
    }

    fetch('/api/keys', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(keyData)
    })
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                document.getElementById('createApiKeyForm').style.display = 'none';
                document.getElementById('newApiKeyResult').style.display = 'block';
                document.getElementById('newApiKeyValue').textContent = data.key;
                showSuccess('API key created! Save it now - it won\'t be shown again.');
                loadApiKeys();
            } else {
                showError('Failed to create API key: ' + data.error);
            }
        })
        .catch(err => showError('Error creating API key: ' + err.message));
}

function copyApiKey() {
    const key = document.getElementById('newApiKeyValue').textContent;
    navigator.clipboard.writeText(key).then(() => {
        showSuccess('API key copied to clipboard!');
    });
}

function revokeApiKey(keyId) {
    if (!confirm('Revoke this API key? This cannot be undone.')) return;

    fetch(`/api/keys/${keyId}`, { method: 'DELETE' })
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                showSuccess('API key revoked');
                loadApiKeys();
            } else {
                showError('Failed to revoke API key');
            }
        });
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
                const status = document.getElementById('killSwitchStatus');
                if (toggle) toggle.checked = data.active;
                if (label) label.textContent = `Kill Switch: ${data.active ? 'ON' : 'OFF'}`;
                if (status) status.textContent = data.active ? 'Active' : 'Inactive';
            }
        });
}

function toggleKillSwitch() {
    const active = document.getElementById('killSwitch').checked;

    fetch('/api/kill-switch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ activate: active })
    })
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                document.getElementById('killSwitchLabel').textContent = `Kill Switch: ${active ? 'ON' : 'OFF'}`;
                document.getElementById('killSwitchStatus').textContent = active ? 'Active' : 'Inactive';
                showSuccess(`Kill switch ${active ? 'activated' : 'deactivated'}`);
            } else {
                showError('Failed to toggle kill switch');
                document.getElementById('killSwitch').checked = !active;
            }
        })
        .catch(() => {
            showError('Error toggling kill switch');
            document.getElementById('killSwitch').checked = !active;
        });
}

// ============================================================================
// SYSTEM STATUS
// ============================================================================

function loadSystemStatus() {
    fetch('/api/status')
        .then(r => r.json())
        .then(data => {
            if (data.version) {
                document.getElementById('systemVersion').textContent = `v${data.version}`;
            }
        });
}

// ============================================================================
// UI HELPERS
// ============================================================================

function formatFeatureName(name) {
    return name.split('_').map(word =>
        word.charAt(0).toUpperCase() + word.slice(1)
    ).join(' ');
}

function formatDate(dateStr) {
    if (!dateStr) return '-';
    const date = new Date(dateStr);
    return date.toLocaleString();
}

function closeModal(modalId) {
    document.getElementById(modalId).style.display = 'none';
}

function showSuccess(message) {
    showNotification(message, 'success');
}

function showError(message) {
    showNotification(message, 'error');
    console.error(message);
}

function showNotification(message, type) {
    const container = document.getElementById('notifications') || document.body;
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
    container.appendChild(notification);

    setTimeout(() => notification.style.opacity = '1', 10);
    setTimeout(() => {
        notification.style.opacity = '0';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}
