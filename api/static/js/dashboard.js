// Feature Flag Dashboard JavaScript

let currentClient = null;
let allClients = {};
let allRulesets = {};

// Initialize dashboard
document.addEventListener('DOMContentLoaded', function() {
    loadClients();
    loadRulesets();
    loadKillSwitchStatus();
    setupEventListeners();
});

// Event Listeners
function setupEventListeners() {
    // Kill switch
    document.getElementById('killSwitch').addEventListener('change', toggleKillSwitch);

    // Client search
    document.getElementById('clientSearch').addEventListener('input', filterClients);

    // Add client button
    document.getElementById('addClientBtn').addEventListener('click', openAddClientModal);

    // Change ruleset button
    document.getElementById('changeRulesetBtn').addEventListener('click', openChangeRulesetModal);

    // Test feature button
    document.getElementById('testFeatureBtn').addEventListener('click', openTestFeatureModal);

    // Modal close buttons
    document.querySelectorAll('.close').forEach(el => {
        el.addEventListener('click', closeModals);
    });

    document.getElementById('cancelRulesetChange').addEventListener('click', closeModals);
    document.getElementById('cancelAddClient').addEventListener('click', closeModals);
    document.getElementById('cancelTestFeature').addEventListener('click', closeModals);

    // Form submissions
    document.getElementById('confirmRulesetChange').addEventListener('click', updateClientRuleset);
    document.getElementById('addClientForm').addEventListener('submit', createNewClient);
    document.getElementById('testFeatureForm').addEventListener('submit', testFeature);

    // Close modals on outside click
    window.addEventListener('click', function(event) {
        if (event.target.classList.contains('modal')) {
            closeModals();
        }
    });
}

// API Calls
async function loadClients() {
    try {
        const response = await fetch('/api/clients');
        const data = await response.json();

        if (data.success) {
            allClients = data.clients;
            renderClientList();
            updateStats();
        } else {
            showError('Failed to load clients: ' + data.error);
        }
    } catch (error) {
        showError('Error loading clients: ' + error.message);
    }
}

async function loadRulesets() {
    try {
        const response = await fetch('/api/rulesets');
        const data = await response.json();

        if (data.success) {
            allRulesets = data.rulesets;
            updateStats();
        } else {
            showError('Failed to load rulesets: ' + data.error);
        }
    } catch (error) {
        showError('Error loading rulesets: ' + error.message);
    }
}

async function loadKillSwitchStatus() {
    try {
        const response = await fetch('/api/kill-switch');
        const data = await response.json();

        if (data.success) {
            const checkbox = document.getElementById('killSwitch');
            checkbox.checked = data.active;
            updateKillSwitchLabel(data.active);
        }
    } catch (error) {
        console.error('Error loading kill switch status:', error);
    }
}

async function toggleKillSwitch(event) {
    const activate = event.target.checked;

    try {
        const response = await fetch('/api/kill-switch', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ activate })
        });

        const data = await response.json();

        if (data.success) {
            updateKillSwitchLabel(activate);
            showSuccess(data.message);
            updateStats();
        } else {
            showError('Failed to toggle kill switch: ' + data.error);
            event.target.checked = !activate; // Revert
        }
    } catch (error) {
        showError('Error toggling kill switch: ' + error.message);
        event.target.checked = !activate; // Revert
    }
}

async function updateClientRuleset() {
    if (!currentClient) return;

    const newRuleset = document.getElementById('rulesetSelect').value;

    try {
        const response = await fetch(`/api/client/${currentClient}/ruleset`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ruleset: newRuleset })
        });

        const data = await response.json();

        if (data.success) {
            showSuccess('Ruleset updated successfully');
            closeModals();
            loadClients();
            loadClientDetails(currentClient);
        } else {
            showError('Failed to update ruleset: ' + data.error);
        }
    } catch (error) {
        showError('Error updating ruleset: ' + error.message);
    }
}

async function createNewClient(event) {
    event.preventDefault();

    const clientId = document.getElementById('newClientId').value;
    const clientName = document.getElementById('newClientName').value;
    const ruleset = document.getElementById('newClientRuleset').value;
    const contact = document.getElementById('newClientContact').value;

    const newClient = {
        client_id: clientId,
        ruleset: ruleset,
        metadata: {
            name: clientName,
            tier: ruleset.replace('_tier', '').replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase()),
            contact: contact,
            signup_date: new Date().toISOString().split('T')[0]
        }
    };

    try {
        const response = await fetch('/api/client', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(newClient)
        });

        const data = await response.json();

        if (data.success) {
            showSuccess('Client created successfully');
            closeModals();
            document.getElementById('addClientForm').reset();
            loadClients();
        } else {
            showError('Failed to create client: ' + data.error);
        }
    } catch (error) {
        showError('Error creating client: ' + error.message);
    }
}

async function testFeature(event) {
    event.preventDefault();

    if (!currentClient) return;

    const featureName = document.getElementById('testFeatureName').value;
    const userId = document.getElementById('testUserId').value;

    let url = `/api/client/${currentClient}/feature/${featureName}`;
    if (userId) {
        url += `?user_id=${userId}`;
    }

    try {
        const response = await fetch(url);
        const data = await response.json();

        if (data.success) {
            const resultDiv = document.getElementById('testResult');
            resultDiv.style.display = 'block';
            resultDiv.className = 'test-result ' + (data.enabled ? 'enabled' : 'disabled');
            resultDiv.innerHTML = `
                <strong>Result:</strong> Feature "${featureName}" is
                <strong>${data.enabled ? 'ENABLED' : 'DISABLED'}</strong>
                for client "${currentClient}"
                ${userId ? ` and user "${userId}"` : ''}
            `;
        } else {
            showError('Error testing feature: ' + data.error);
        }
    } catch (error) {
        showError('Error testing feature: ' + error.message);
    }
}

async function loadClientDetails(clientId) {
    try {
        const response = await fetch(`/api/client/${clientId}`);
        const data = await response.json();

        if (data.success) {
            currentClient = clientId;
            renderClientDetails(data.client);
        } else {
            showError('Failed to load client details: ' + data.error);
        }
    } catch (error) {
        showError('Error loading client details: ' + error.message);
    }
}

// Rendering Functions
function renderClientList() {
    const clientList = document.getElementById('clientList');
    clientList.innerHTML = '';

    const clientIds = Object.keys(allClients);

    if (clientIds.length === 0) {
        clientList.innerHTML = '<div class="loading">No clients found</div>';
        return;
    }

    clientIds.forEach(clientId => {
        const client = allClients[clientId];
        const metadata = client.metadata || {};

        const clientItem = document.createElement('div');
        clientItem.className = 'client-item';
        if (clientId === currentClient) {
            clientItem.classList.add('active');
        }

        clientItem.innerHTML = `
            <h3>${metadata.name || clientId}</h3>
            <p>${clientId}</p>
            <span class="tier-badge tier-${metadata.tier || 'Unknown'}">${metadata.tier || 'Unknown'}</span>
            <p style="margin-top: 5px; font-size: 11px;">
                ${client.feature_count || 0} features
            </p>
        `;

        clientItem.addEventListener('click', () => loadClientDetails(clientId));
        clientList.appendChild(clientItem);
    });
}

function renderClientDetails(client) {
    // Hide welcome message, show details
    document.getElementById('welcomeMessage').style.display = 'none';
    document.getElementById('clientDetails').style.display = 'block';

    // Update client info
    document.getElementById('clientName').textContent = client.metadata.name || client.client_id;
    document.getElementById('clientId').textContent = client.client_id;
    document.getElementById('clientTier').textContent = client.metadata.tier || 'Unknown';
    document.getElementById('clientTier').className = `tier-badge tier-${client.metadata.tier}`;

    document.getElementById('currentRuleset').textContent = client.ruleset || '-';
    document.getElementById('rulesetDescription').textContent = client.ruleset_description || '-';
    document.getElementById('clientContact').textContent = client.metadata.contact || '-';
    document.getElementById('clientSignupDate').textContent = client.metadata.signup_date || '-';
    document.getElementById('featureCount').textContent = client.feature_count || 0;

    // Render features
    const featuresList = document.getElementById('featuresList');
    featuresList.innerHTML = '';

    if (client.features && client.features.length > 0) {
        client.features.forEach(feature => {
            const featureCard = document.createElement('div');
            featureCard.className = 'feature-card';
            featureCard.innerHTML = `
                <h4>${feature}</h4>
                <div class="feature-status">✓ Enabled</div>
            `;
            featuresList.appendChild(featureCard);
        });
    } else {
        featuresList.innerHTML = '<p>No features available</p>';
    }

    // Update active state in sidebar
    document.querySelectorAll('.client-item').forEach(item => {
        item.classList.remove('active');
        if (item.textContent.includes(client.client_id)) {
            item.classList.add('active');
        }
    });
}

function filterClients() {
    const searchTerm = document.getElementById('clientSearch').value.toLowerCase();
    const clientItems = document.querySelectorAll('.client-item');

    clientItems.forEach(item => {
        const text = item.textContent.toLowerCase();
        if (text.includes(searchTerm)) {
            item.style.display = 'block';
        } else {
            item.style.display = 'none';
        }
    });
}

function updateStats() {
    document.getElementById('totalClients').textContent = Object.keys(allClients).length;
    document.getElementById('totalRulesets').textContent = Object.keys(allRulesets).length;

    const killSwitch = document.getElementById('killSwitch').checked;
    document.getElementById('killSwitchStatus').textContent = killSwitch ? 'Active' : 'Inactive';
    document.getElementById('killSwitchStatus').style.color = killSwitch ? '#f44336' : '#4caf50';
}

function updateKillSwitchLabel(active) {
    const label = document.getElementById('killSwitchLabel');
    label.textContent = `Kill Switch: ${active ? 'ON (All using baseline)' : 'OFF'}`;
    label.style.color = active ? '#f44336' : 'white';
}

// Modal Functions
function openChangeRulesetModal() {
    if (!currentClient) return;

    const modal = document.getElementById('changeRulesetModal');
    const select = document.getElementById('rulesetSelect');
    const clientName = allClients[currentClient]?.metadata?.name || currentClient;

    document.getElementById('modalClientName').textContent = clientName;

    // Populate ruleset options
    select.innerHTML = '';
    Object.keys(allRulesets).forEach(rulesetName => {
        const option = document.createElement('option');
        option.value = rulesetName;
        option.textContent = `${rulesetName} - ${allRulesets[rulesetName].description}`;
        if (rulesetName === allClients[currentClient].ruleset) {
            option.selected = true;
        }
        select.appendChild(option);
    });

    modal.style.display = 'block';
}

function openAddClientModal() {
    const modal = document.getElementById('addClientModal');
    const select = document.getElementById('newClientRuleset');

    // Populate ruleset options
    select.innerHTML = '';
    Object.keys(allRulesets).forEach(rulesetName => {
        const option = document.createElement('option');
        option.value = rulesetName;
        option.textContent = `${rulesetName} - ${allRulesets[rulesetName].description}`;
        select.appendChild(option);
    });

    modal.style.display = 'block';
}

function openTestFeatureModal() {
    if (!currentClient) return;

    const modal = document.getElementById('testFeatureModal');
    document.getElementById('testResult').style.display = 'none';
    document.getElementById('testFeatureForm').reset();
    modal.style.display = 'block';
}

function closeModals() {
    document.querySelectorAll('.modal').forEach(modal => {
        modal.style.display = 'none';
    });
}

// Utility Functions
function showSuccess(message) {
    alert('✓ ' + message);
}

function showError(message) {
    alert('✗ ' + message);
}
