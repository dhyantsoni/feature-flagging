/**
 * nixo Feature Flag Dashboard JavaScript
 *
 * Provides UI functionality for Features, Rulesets, and Clients tabs
 * with support for ruleset inheritance, feature categories, and client overrides.
 */

// =============================================================================
// State Management
// =============================================================================

const nixoState = {
    features: [],
    featuresByCategory: {},
    categories: [],
    rulesets: [],
    clients: [],
    currentRuleset: null,
    currentClient: null,
    lastSync: null,
    loading: {
        features: false,
        rulesets: false,
        clients: false
    }
};

// =============================================================================
// Initialization
// =============================================================================

function initNixo() {
    console.log('Initializing nixo dashboard...');
    setupNixoEventListeners();
}

function setupNixoEventListeners() {
    // Feature tab buttons
    document.getElementById('syncFeaturesBtn')?.addEventListener('click', syncFeatures);
    document.getElementById('expandAllCategories')?.addEventListener('click', expandAllCategories);
    document.getElementById('collapseAllCategories')?.addEventListener('click', collapseAllCategories);

    // Ruleset tab buttons
    document.getElementById('createRulesetBtn')?.addEventListener('click', showCreateRulesetModal);
    document.getElementById('rulesetSearch')?.addEventListener('input', filterRulesets);
    document.getElementById('rulesetFilter')?.addEventListener('change', filterRulesets);
    document.getElementById('templatesOnlyCheckbox')?.addEventListener('change', filterRulesets);

    // Client tab buttons
    document.getElementById('bulkAssignBtn')?.addEventListener('click', showBulkAssignModal);
    document.getElementById('nixoClientSearch')?.addEventListener('input', filterNixoClients);
    document.getElementById('clientRulesetFilter')?.addEventListener('change', filterNixoClients);

    // Modal forms
    document.getElementById('createRulesetForm')?.addEventListener('submit', handleCreateRuleset);
    document.getElementById('editRulesetForm')?.addEventListener('submit', handleEditRuleset);
    document.getElementById('addOverrideForm')?.addEventListener('submit', handleAddOverride);

    // Modal cancel buttons
    document.querySelectorAll('[data-dismiss="modal"]').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const modal = e.target.closest('.modal');
            if (modal) modal.style.display = 'none';
        });
    });
}

// =============================================================================
// Tab Loading Functions
// =============================================================================

function loadNixoFeatures() {
    if (nixoState.loading.features) return;
    nixoState.loading.features = true;

    const container = document.getElementById('nixoFeaturesContainer');
    if (container) {
        container.innerHTML = '<div class="loading">Loading features...</div>';
    }

    fetch('/api/nixo/features')
        .then(r => r.json())
        .then(data => {
            nixoState.loading.features = false;
            if (data.success) {
                nixoState.features = data.features;
                organizeFeaturesByCategory();
                renderNixoFeatures();
                updateFeatureStats();
            } else {
                showNixoError('Failed to load features: ' + data.error);
            }
        })
        .catch(err => {
            nixoState.loading.features = false;
            showNixoError('Error loading features: ' + err.message);
        });
}

function loadNixoRulesets() {
    if (nixoState.loading.rulesets) return;
    nixoState.loading.rulesets = true;

    const container = document.getElementById('nixoRulesetsGrid');
    if (container) {
        container.innerHTML = '<div class="loading">Loading rulesets...</div>';
    }

    fetch('/api/nixo/rulesets')
        .then(r => r.json())
        .then(data => {
            nixoState.loading.rulesets = false;
            if (data.success) {
                nixoState.rulesets = data.rulesets;
                renderNixoRulesets();
                populateRulesetDropdowns();
            } else {
                showNixoError('Failed to load rulesets: ' + data.error);
            }
        })
        .catch(err => {
            nixoState.loading.rulesets = false;
            showNixoError('Error loading rulesets: ' + err.message);
        });
}

function loadNixoClients() {
    if (nixoState.loading.clients) return;
    nixoState.loading.clients = true;

    const container = document.getElementById('nixoClientsTable');
    if (container) {
        container.innerHTML = '<tr><td colspan="5" class="loading">Loading clients...</td></tr>';
    }

    fetch('/api/nixo/clients')
        .then(r => r.json())
        .then(data => {
            nixoState.loading.clients = false;
            if (data.success) {
                nixoState.clients = data.clients;
                renderNixoClients();
            } else {
                showNixoError('Failed to load clients: ' + data.error);
            }
        })
        .catch(err => {
            nixoState.loading.clients = false;
            showNixoError('Error loading clients: ' + err.message);
        });
}

// =============================================================================
// Feature Tab Functions
// =============================================================================

function organizeFeaturesByCategory() {
    nixoState.featuresByCategory = {};
    nixoState.categories = [];

    nixoState.features.forEach(feature => {
        const category = feature.category || 'Other';
        if (!nixoState.featuresByCategory[category]) {
            nixoState.featuresByCategory[category] = [];
            nixoState.categories.push(category);
        }
        nixoState.featuresByCategory[category].push(feature);
    });

    nixoState.categories.sort();
}

function renderNixoFeatures() {
    const container = document.getElementById('nixoFeaturesContainer');
    if (!container) return;

    if (nixoState.features.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <p>No features found. Click "Sync from Codebase" to discover features.</p>
            </div>
        `;
        return;
    }

    let html = '';
    nixoState.categories.forEach(category => {
        const features = nixoState.featuresByCategory[category];
        const enforcedCount = features.filter(f => f.is_enforced).length;

        html += `
            <div class="category-section" data-category="${category}">
                <div class="category-header" onclick="toggleCategory('${category}')">
                    <h3>
                        <span class="category-toggle">&#9660;</span>
                        ${category}
                        <span class="category-count">(${features.length})</span>
                        ${enforcedCount > 0 ? `<span class="enforced-badge">${enforcedCount} enforced</span>` : ''}
                    </h3>
                </div>
                <div class="category-features" id="category-${category.replace(/\s+/g, '-')}">
                    ${features.map(f => renderFeatureRow(f)).join('')}
                </div>
            </div>
        `;
    });

    container.innerHTML = html;
}

function renderFeatureRow(feature) {
    const enforcedClass = feature.is_enforced ? 'enforced' : '';
    const locations = feature.enforcement_locations || [];

    return `
        <div class="feature-row ${enforcedClass}">
            <div class="feature-info">
                <span class="feature-name">${feature.name}</span>
                <span class="feature-description">${feature.description || ''}</span>
            </div>
            <div class="feature-status">
                ${feature.is_enforced ? `
                    <span class="enforced-tag" title="Enforced in code">ENFORCED</span>
                    ${locations.length > 0 ? `
                        <div class="enforcement-locations">
                            ${locations.slice(0, 3).map(loc =>
                                `<span class="location">${loc.file}:${loc.line}</span>`
                            ).join('')}
                            ${locations.length > 3 ? `<span class="more">+${locations.length - 3} more</span>` : ''}
                        </div>
                    ` : ''}
                ` : ''}
            </div>
        </div>
    `;
}

function toggleCategory(category) {
    const section = document.querySelector(`[data-category="${category}"]`);
    const content = document.getElementById(`category-${category.replace(/\s+/g, '-')}`);
    const toggle = section?.querySelector('.category-toggle');

    if (content && toggle) {
        const isHidden = content.style.display === 'none';
        content.style.display = isHidden ? 'block' : 'none';
        toggle.innerHTML = isHidden ? '&#9660;' : '&#9658;';
    }
}

function expandAllCategories() {
    document.querySelectorAll('.category-features').forEach(el => {
        el.style.display = 'block';
    });
    document.querySelectorAll('.category-toggle').forEach(el => {
        el.innerHTML = '&#9660;';
    });
}

function collapseAllCategories() {
    document.querySelectorAll('.category-features').forEach(el => {
        el.style.display = 'none';
    });
    document.querySelectorAll('.category-toggle').forEach(el => {
        el.innerHTML = '&#9658;';
    });
}

function syncFeatures() {
    const btn = document.getElementById('syncFeaturesBtn');
    if (btn) {
        btn.disabled = true;
        btn.textContent = 'Syncing...';
    }

    fetch('/api/nixo/features/sync', { method: 'POST' })
        .then(r => r.json())
        .then(data => {
            if (btn) {
                btn.disabled = false;
                btn.textContent = 'Sync from Codebase';
            }
            if (data.success) {
                showNixoSuccess(`Synced ${data.synced} features`);
                nixoState.lastSync = data.synced_at;
                updateFeatureStats();
                loadNixoFeatures();
            } else {
                showNixoError('Sync failed: ' + data.error);
            }
        })
        .catch(err => {
            if (btn) {
                btn.disabled = false;
                btn.textContent = 'Sync from Codebase';
            }
            showNixoError('Sync error: ' + err.message);
        });
}

function updateFeatureStats() {
    const totalEl = document.getElementById('nixoTotalFeatures');
    const enforcedEl = document.getElementById('nixoEnforcedCount');
    const lastSyncEl = document.getElementById('nixoLastSync');

    if (totalEl) totalEl.textContent = nixoState.features.length;
    if (enforcedEl) {
        enforcedEl.textContent = nixoState.features.filter(f => f.is_enforced).length;
    }
    if (lastSyncEl && nixoState.lastSync) {
        lastSyncEl.textContent = new Date(nixoState.lastSync).toLocaleString();
    }
}

// =============================================================================
// Ruleset Tab Functions
// =============================================================================

function renderNixoRulesets() {
    const container = document.getElementById('nixoRulesetsGrid');
    if (!container) return;

    if (nixoState.rulesets.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <p>No rulesets found. Create one to get started.</p>
            </div>
        `;
        return;
    }

    const html = nixoState.rulesets.map(ruleset => renderRulesetCard(ruleset)).join('');
    container.innerHTML = html;
}

function renderRulesetCard(ruleset) {
    const isTemplate = ruleset.is_template;
    const featureCount = ruleset.direct_feature_count || 0;
    const clientCount = ruleset.client_count || 0;
    const parentName = ruleset.parent_name;

    return `
        <div class="ruleset-card" data-ruleset-id="${ruleset.id}" style="--ruleset-color: ${ruleset.color || '#6366f1'}">
            <div class="ruleset-header">
                <h3>${ruleset.display_name}</h3>
                ${isTemplate ? '<span class="template-badge">Template</span>' : '<span class="custom-badge">Custom</span>'}
            </div>
            <div class="ruleset-body">
                <p class="ruleset-description">${ruleset.description || ''}</p>
                <div class="ruleset-stats">
                    <span>${featureCount} features</span>
                    <span>${clientCount} clients</span>
                </div>
                ${parentName ? `<div class="ruleset-inherits">Inherits: ${parentName}</div>` : ''}
            </div>
            <div class="ruleset-actions">
                <button class="btn btn-sm" onclick="editRuleset('${ruleset.id}')">Edit</button>
                <button class="btn btn-sm" onclick="cloneRuleset('${ruleset.id}')">Clone</button>
                ${!isTemplate ? `<button class="btn btn-sm btn-danger" onclick="deleteRuleset('${ruleset.id}')">Delete</button>` : ''}
            </div>
        </div>
    `;
}

function filterRulesets() {
    const search = document.getElementById('rulesetSearch')?.value.toLowerCase() || '';
    const templatesOnly = document.getElementById('templatesOnlyCheckbox')?.checked || false;

    const filtered = nixoState.rulesets.filter(r => {
        const matchesSearch = r.name.toLowerCase().includes(search) ||
            r.display_name.toLowerCase().includes(search) ||
            (r.description || '').toLowerCase().includes(search);
        const matchesTemplate = !templatesOnly || r.is_template;
        return matchesSearch && matchesTemplate;
    });

    const container = document.getElementById('nixoRulesetsGrid');
    if (container) {
        container.innerHTML = filtered.map(r => renderRulesetCard(r)).join('');
    }
}

function showCreateRulesetModal() {
    const modal = document.getElementById('createRulesetModal');
    if (modal) {
        // Reset form
        document.getElementById('createRulesetForm')?.reset();

        // Populate inheritance dropdown
        populateInheritanceDropdown('createRulesetInherits');

        // Populate features checklist
        populateFeatureChecklist('createRulesetFeatures');

        modal.style.display = 'block';
    }
}

function handleCreateRuleset(e) {
    e.preventDefault();

    const name = document.getElementById('createRulesetName').value.trim();
    const displayName = document.getElementById('createRulesetDisplayName').value.trim();
    const description = document.getElementById('createRulesetDescription').value;
    const color = document.getElementById('createRulesetColor').value;
    const inheritsFrom = document.getElementById('createRulesetInherits').value || null;

    // Get selected features
    const features = [];
    document.querySelectorAll('#createRulesetFeatures input[type="checkbox"]:checked').forEach(cb => {
        features.push({ feature_name: cb.value, enabled: true });
    });

    fetch('/api/nixo/rulesets', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            name,
            display_name: displayName,
            description,
            color,
            inherits_from: inheritsFrom,
            features
        })
    })
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                closeModal('createRulesetModal');
                showNixoSuccess('Ruleset created successfully');
                loadNixoRulesets();
            } else {
                showNixoError('Failed to create ruleset: ' + data.error);
            }
        })
        .catch(err => showNixoError('Error: ' + err.message));
}

function editRuleset(rulesetId) {
    // Fetch ruleset details
    fetch(`/api/nixo/rulesets/${rulesetId}`)
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                nixoState.currentRuleset = data.ruleset;
                showEditRulesetModal(data.ruleset);
            } else {
                showNixoError('Failed to load ruleset');
            }
        });
}

function showEditRulesetModal(ruleset) {
    const modal = document.getElementById('editRulesetModal');
    if (!modal) return;

    // Populate form fields
    document.getElementById('editRulesetId').value = ruleset.id;
    document.getElementById('editRulesetName').value = ruleset.name;
    document.getElementById('editRulesetDisplayName').value = ruleset.display_name;
    document.getElementById('editRulesetDescription').value = ruleset.description || '';
    document.getElementById('editRulesetColor').value = ruleset.color || '#6366f1';

    // Populate inheritance dropdown
    populateInheritanceDropdown('editRulesetInherits', ruleset.id);
    document.getElementById('editRulesetInherits').value = ruleset.inherits_from || '';

    // Load and populate features
    fetch(`/api/nixo/rulesets/${ruleset.id}/features`)
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                populateFeatureChecklist('editRulesetFeatures', data.features);
            }
        });

    modal.style.display = 'block';
}

function handleEditRuleset(e) {
    e.preventDefault();

    const rulesetId = document.getElementById('editRulesetId').value;
    const displayName = document.getElementById('editRulesetDisplayName').value.trim();
    const description = document.getElementById('editRulesetDescription').value;
    const color = document.getElementById('editRulesetColor').value;
    const inheritsFrom = document.getElementById('editRulesetInherits').value || null;

    // Update ruleset metadata
    fetch(`/api/nixo/rulesets/${rulesetId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            display_name: displayName,
            description,
            color,
            inherits_from: inheritsFrom
        })
    })
        .then(r => r.json())
        .then(data => {
            if (!data.success) {
                throw new Error(data.error);
            }

            // Update features
            const features = [];
            document.querySelectorAll('#editRulesetFeatures input[type="checkbox"]:checked').forEach(cb => {
                features.push({ feature_name: cb.value, enabled: true });
            });

            return fetch(`/api/nixo/rulesets/${rulesetId}/features`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ features })
            });
        })
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                closeModal('editRulesetModal');
                showNixoSuccess('Ruleset updated successfully');
                loadNixoRulesets();
            } else {
                showNixoError('Failed to update features: ' + data.error);
            }
        })
        .catch(err => showNixoError('Error: ' + err.message));
}

function cloneRuleset(rulesetId) {
    const name = prompt('Enter name for the cloned ruleset:');
    if (!name) return;

    const displayName = prompt('Enter display name:', name);
    if (!displayName) return;

    fetch(`/api/nixo/rulesets/${rulesetId}/clone`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, display_name: displayName })
    })
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                showNixoSuccess('Ruleset cloned successfully');
                loadNixoRulesets();
            } else {
                showNixoError('Failed to clone: ' + data.error);
            }
        })
        .catch(err => showNixoError('Error: ' + err.message));
}

function deleteRuleset(rulesetId) {
    if (!confirm('Are you sure you want to delete this ruleset?')) return;

    fetch(`/api/nixo/rulesets/${rulesetId}`, { method: 'DELETE' })
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                showNixoSuccess('Ruleset deleted');
                loadNixoRulesets();
            } else {
                showNixoError('Failed to delete: ' + data.error);
            }
        })
        .catch(err => showNixoError('Error: ' + err.message));
}

function populateInheritanceDropdown(selectId, excludeId = null) {
    const select = document.getElementById(selectId);
    if (!select) return;

    let html = '<option value="">No inheritance</option>';
    nixoState.rulesets.forEach(r => {
        if (r.id !== excludeId) {
            html += `<option value="${r.id}">${r.display_name}</option>`;
        }
    });
    select.innerHTML = html;
}

function populateFeatureChecklist(containerId, enabledFeatures = []) {
    const container = document.getElementById(containerId);
    if (!container) return;

    const enabledSet = new Set(enabledFeatures.map(f => f.feature_name));

    let html = '';
    nixoState.categories.forEach(category => {
        const features = nixoState.featuresByCategory[category];
        html += `<div class="feature-category-group">
            <h4>${category}</h4>
            <div class="feature-checkboxes">
        `;
        features.forEach(f => {
            const checked = enabledSet.has(f.name) ? 'checked' : '';
            const inherited = enabledFeatures.find(ef => ef.feature_name === f.name && ef.is_inherited);
            html += `
                <label class="feature-checkbox ${inherited ? 'inherited' : ''}">
                    <input type="checkbox" value="${f.name}" ${checked}>
                    ${f.name}
                    ${inherited ? '<span class="inherited-tag">(inherited)</span>' : ''}
                </label>
            `;
        });
        html += '</div></div>';
    });
    container.innerHTML = html;
}

function populateRulesetDropdowns() {
    const selects = document.querySelectorAll('.ruleset-dropdown');
    selects.forEach(select => {
        let html = '<option value="">Select a ruleset</option>';
        nixoState.rulesets.forEach(r => {
            html += `<option value="${r.id}">${r.display_name}</option>`;
        });
        select.innerHTML = html;
    });
}

// =============================================================================
// Client Tab Functions
// =============================================================================

function renderNixoClients() {
    const tbody = document.getElementById('nixoClientsTable');
    if (!tbody) return;

    if (nixoState.clients.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="5" class="empty-state">No clients found</td>
            </tr>
        `;
        return;
    }

    const html = nixoState.clients.map(client => renderClientRow(client)).join('');
    tbody.innerHTML = html;
}

function renderClientRow(client) {
    const overrideCount = client.override_count || 0;
    const overrideDisplay = overrideCount > 0 ?
        `<span class="override-badge">${overrideCount > 0 ? '+' : ''}${overrideCount}</span>` : '-';

    return `
        <tr data-client-id="${client.client_id}">
            <td class="client-name">${client.client_id}</td>
            <td>
                <span class="ruleset-badge" style="background-color: ${client.ruleset_color || '#6366f1'}20; color: ${client.ruleset_color || '#6366f1'}">
                    ${client.ruleset_display_name || client.ruleset_name || 'None'}
                </span>
            </td>
            <td>${overrideDisplay}</td>
            <td>-</td>
            <td>
                <button class="btn btn-sm" onclick="viewClient('${client.client_id}')">View</button>
            </td>
        </tr>
    `;
}

function filterNixoClients() {
    const search = document.getElementById('nixoClientSearch')?.value.toLowerCase() || '';
    const rulesetId = document.getElementById('clientRulesetFilter')?.value || '';

    const filtered = nixoState.clients.filter(c => {
        const matchesSearch = c.client_id.toLowerCase().includes(search);
        const matchesRuleset = !rulesetId || c.ruleset_id === rulesetId;
        return matchesSearch && matchesRuleset;
    });

    const tbody = document.getElementById('nixoClientsTable');
    if (tbody) {
        tbody.innerHTML = filtered.map(c => renderClientRow(c)).join('');
    }
}

function viewClient(clientId) {
    fetch(`/api/nixo/clients/${clientId}`)
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                nixoState.currentClient = {
                    ...data.client,
                    features: data.features,
                    overrides: data.overrides
                };
                showClientPanel(nixoState.currentClient);
            } else {
                showNixoError('Failed to load client');
            }
        });
}

function showClientPanel(client) {
    const panel = document.getElementById('nixoClientPanel');
    if (!panel) return;

    const features = client.features || [];
    const overrides = client.overrides || [];
    const enabledCount = features.filter(f => f.enabled).length;

    panel.innerHTML = `
        <div class="client-panel-header">
            <h2>${client.client_id}</h2>
            <button class="close-panel" onclick="closeClientPanel()">&times;</button>
        </div>

        <div class="client-ruleset-section">
            <label>Assigned Ruleset:</label>
            <select id="clientRulesetSelect" class="ruleset-dropdown" onchange="changeClientRuleset('${client.client_id}')">
                ${nixoState.rulesets.map(r =>
                    `<option value="${r.id}" ${r.id === client.ruleset_id ? 'selected' : ''}>${r.display_name}</option>`
                ).join('')}
            </select>
        </div>

        <div class="client-overrides-section">
            <div class="section-header">
                <h3>Overrides (${overrides.length})</h3>
                <button class="btn btn-sm" onclick="showAddOverrideModal('${client.client_id}')">+ Add Override</button>
            </div>
            <div class="overrides-list">
                ${overrides.length === 0 ? '<p class="empty">No overrides</p>' :
                    overrides.map(o => `
                        <div class="override-item">
                            <span class="feature-name">${o.feature_name}</span>
                            <span class="override-status ${o.enabled ? 'enabled' : 'disabled'}">${o.enabled ? 'ENABLED' : 'DISABLED'}</span>
                            <span class="override-reason">${o.reason || ''}</span>
                            ${o.expires_at ? `<span class="override-expires">Exp: ${new Date(o.expires_at).toLocaleDateString()}</span>` : ''}
                            <button class="btn btn-sm btn-danger" onclick="removeOverride('${client.client_id}', '${o.feature_name}')">&times;</button>
                        </div>
                    `).join('')
                }
            </div>
        </div>

        <div class="client-features-section">
            <h3>Resolved Features (${enabledCount} enabled)</h3>
            <div class="resolved-features-list">
                ${features.map(f => `
                    <div class="resolved-feature ${f.enabled ? 'enabled' : 'disabled'}">
                        <span class="feature-check">${f.enabled ? '&#10003;' : '&#10005;'}</span>
                        <span class="feature-name">${f.feature_name}</span>
                        <span class="feature-source ${f.source}">${f.source}</span>
                    </div>
                `).join('')}
            </div>
        </div>
    `;

    panel.style.display = 'block';
}

function closeClientPanel() {
    const panel = document.getElementById('nixoClientPanel');
    if (panel) panel.style.display = 'none';
    nixoState.currentClient = null;
}

function changeClientRuleset(clientId) {
    const rulesetId = document.getElementById('clientRulesetSelect').value;

    fetch(`/api/nixo/clients/${clientId}/ruleset`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ruleset_id: rulesetId })
    })
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                showNixoSuccess('Ruleset updated');
                loadNixoClients();
                viewClient(clientId); // Refresh panel
            } else {
                showNixoError('Failed to update: ' + data.error);
            }
        });
}

function showAddOverrideModal(clientId) {
    const modal = document.getElementById('addOverrideModal');
    if (modal) {
        document.getElementById('overrideClientId').value = clientId;
        document.getElementById('addOverrideForm')?.reset();

        // Populate features dropdown
        const select = document.getElementById('overrideFeatureSelect');
        if (select) {
            select.innerHTML = nixoState.features.map(f =>
                `<option value="${f.name}">${f.name}</option>`
            ).join('');
        }

        modal.style.display = 'block';
    }
}

function handleAddOverride(e) {
    e.preventDefault();

    const clientId = document.getElementById('overrideClientId').value;
    const featureName = document.getElementById('overrideFeatureSelect').value;
    const enabled = document.getElementById('overrideEnabled').value === 'true';
    const reason = document.getElementById('overrideReason').value;
    const expiresAt = document.getElementById('overrideExpires').value || null;

    fetch(`/api/nixo/clients/${clientId}/overrides`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            feature_name: featureName,
            enabled,
            reason,
            expires_at: expiresAt
        })
    })
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                closeModal('addOverrideModal');
                showNixoSuccess('Override added');
                viewClient(clientId); // Refresh panel
            } else {
                showNixoError('Failed to add override: ' + data.error);
            }
        });
}

function removeOverride(clientId, featureName) {
    if (!confirm(`Remove override for ${featureName}?`)) return;

    fetch(`/api/nixo/clients/${clientId}/overrides/${featureName}`, { method: 'DELETE' })
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                showNixoSuccess('Override removed');
                viewClient(clientId);
            } else {
                showNixoError('Failed to remove: ' + data.error);
            }
        });
}

function showBulkAssignModal() {
    // TODO: Implement bulk assignment modal
    alert('Bulk assignment coming soon');
}

// =============================================================================
// Utility Functions
// =============================================================================

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) modal.style.display = 'none';
}

function showNixoSuccess(message) {
    showNotification(message, 'success');
}

function showNixoError(message) {
    showNotification(message, 'error');
    console.error(message);
}

// Use existing notification system from dashboard.js
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

// Export for use in tab switching
window.loadNixoFeatures = loadNixoFeatures;
window.loadNixoRulesets = loadNixoRulesets;
window.loadNixoClients = loadNixoClients;
window.initNixo = initNixo;
