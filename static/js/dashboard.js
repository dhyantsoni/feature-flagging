// Feature Flag Dashboard JavaScript

let currentProject = null;
let currentClient = null;
let allClients = [];
let allRulesets = [];
let allProjects = [];

// Initialize dashboard
document.addEventListener('DOMContentLoaded', function() {
    loadClients();
    loadRulesets();
    loadProjects();
    updateKillSwitchStatus();
    setupEventListeners();
});

// Event Listeners
function setupEventListeners() {
    // Kill switch
    document.getElementById('killSwitch').addEventListener('change', toggleKillSwitch);

    // Client search
    if (document.getElementById('clientSearch')) {
        document.getElementById('clientSearch').addEventListener('input', filterClients);
    }

    // Close modals on outside click
    window.addEventListener('click', function(event) {
        if (event.target.classList.contains('modal')) {
            event.target.classList.remove('active');
        }
    });
}

// ============================================================================
// PROJECT MANAGEMENT
// ============================================================================

function loadProjects() {
    fetch('/api/projects')
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                allProjects = data.projects || [];
                updateProjectSelector();
                document.getElementById('totalProjects').textContent = allProjects.length;
            }
        })
        .catch(err => console.error('Error loading projects:', err));
}

function updateProjectSelector() {
    const select = document.getElementById('projectSelect');
    select.innerHTML = '<option value="">Select Project...</option>';
    allProjects.forEach(p => {
        select.innerHTML += `<option value="${p.id}">${p.name}</option>`;
    });
}

function selectProject() {
    const projectId = document.getElementById('projectSelect').value;
    if (!projectId) {
        document.getElementById('welcomeMessage').style.display = 'block';
        document.getElementById('projectView').style.display = 'none';
        document.getElementById('clientDetails').style.display = 'none';
        return;
    }

    currentProject = allProjects.find(p => p.id === projectId);
    document.getElementById('projectName').textContent = currentProject.name;
    document.getElementById('projectRepo').textContent = currentProject.repository_url || 'N/A';
    
    document.getElementById('welcomeMessage').style.display = 'none';
    document.getElementById('projectView').style.display = 'block';
    document.getElementById('clientDetails').style.display = 'none';

    loadProjectData(projectId);
}

function loadProjectData(projectId) {
    fetch(`/api/projects/${projectId}/graph/data`)
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                visualizeGraph(data.graph);
            }
        })
        .catch(err => console.error('Error loading project data:', err));

    fetch(`/api/projects/${projectId}/functions`)
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                displayFunctions(data.functions);
                document.getElementById('projectFunctions').textContent = data.functions.length;
            }
        })
        .catch(err => console.error('Error loading functions:', err));
}

function analyzeProject() {
    if (!currentProject) return;
    
    const projectId = currentProject.id;
    const directoryPath = prompt('Enter project directory path:');
    
    if (!directoryPath) return;

    const btn = event.target;
    btn.disabled = true;
    btn.textContent = '🔄 Analyzing...';

    fetch(`/api/projects/${projectId}/analyze-full`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ directory_path: directoryPath })
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            alert('✅ Project analyzed successfully!');
            document.getElementById('projectFiles').textContent = data.analysis.total_files;
            document.getElementById('projectFunctions').textContent = data.analysis.statistics.total_functions;
            document.getElementById('projectFeatures').textContent = data.analysis.features.length;
            loadProjectData(projectId);
        } else {
            alert('❌ Error: ' + data.error);
        }
    })
    .catch(err => {
        console.error('Error:', err);
        alert('❌ Analysis failed');
    })
    .finally(() => {
        btn.disabled = false;
        btn.textContent = '🔍 Analyze Project';
    });
}

function displayFunctions(functions) {
    const list = document.getElementById('functionsList');
    if (!functions.length) {
        list.innerHTML = '<p>No functions found</p>';
        return;
    }

    list.innerHTML = functions.map(f => `
        <div class="feature-card">
            <div class="feature-name">${f.function_name}</div>
            <p style="font-size: 11px; color: #666;">
                ${f.file_path}
            </p>
            <p style="font-size: 11px; margin-top: 5px;">
                ${f.is_feature_flagged ? '🚩 Feature' : ''}
                ${f.is_helper ? '🔧 Helper' : ''}
                ${f.is_shared_helper ? '🔗 Shared' : ''}
            </p>
        </div>
    `).join('');
}

function visualizeGraph(graphData) {
    // Simple D3 visualization
    if (!graphData || !graphData.nodes) return;

    const svg = document.getElementById('graphSvg');
    if (!svg) return;
    
    svg.innerHTML = ''; // Clear previous

    const width = svg.clientWidth;
    const height = svg.clientHeight;

    const simulation = d3.forceSimulation(graphData.nodes)
        .force('link', d3.forceLink(graphData.links).id(d => d.id).distance(100))
        .force('charge', d3.forceManyBody().strength(-300))
        .force('center', d3.forceCenter(width / 2, height / 2));

    const g = d3.select(svg);

    // Links
    const link = g.selectAll('.link')
        .data(graphData.links)
        .enter().append('line')
        .attr('class', 'link')
        .attr('stroke', '#ffb6d9')
        .attr('stroke-width', 2)
        .attr('marker-end', 'url(#arrowhead)');

    // Define arrowhead marker
    g.append('defs').append('marker')
        .attr('id', 'arrowhead')
        .attr('markerWidth', 10)
        .attr('markerHeight', 10)
        .attr('refX', 20)
        .attr('refY', 3)
        .attr('orient', 'auto')
        .append('polygon')
        .attr('points', '0 0, 10 3, 0 6')
        .attr('fill', '#ff69b4');

    // Nodes
    const node = g.selectAll('.node')
        .data(graphData.nodes)
        .enter().append('circle')
        .attr('class', 'node')
        .attr('r', d => Math.min(d.size * 5, 20))
        .attr('fill', '#ffb6d9')
        .attr('stroke', '#ff69b4')
        .attr('stroke-width', 2)
        .call(d3.drag()
            .on('start', dragstarted)
            .on('drag', dragged)
            .on('end', dragended));

    // Labels
    const labels = g.selectAll('.label')
        .data(graphData.nodes)
        .enter().append('text')
        .attr('class', 'label')
        .attr('text-anchor', 'middle')
        .attr('dy', '.3em')
        .attr('font-size', '11px')
        .attr('fill', '#333')
        .text(d => d.label);

    simulation.on('tick', () => {
        link
            .attr('x1', d => d.source.x)
            .attr('y1', d => d.source.y)
            .attr('x2', d => d.target.x)
            .attr('y2', d => d.target.y);

        node
            .attr('cx', d => d.x)
            .attr('cy', d => d.y);

        labels
            .attr('x', d => d.x)
            .attr('y', d => d.y);
    });

    function dragstarted(event, d) {
        if (!event.active) simulation.alphaTarget(0.3).restart();
        d.fx = d.x;
        d.fy = d.y;
    }

    function dragged(event, d) {
        d.fx = event.x;
        d.fy = event.y;
    }

    function dragended(event, d) {
        if (!event.active) simulation.alphaTarget(0);
        d.fx = null;
        d.fy = null;
    }
}

function switchTab(tabName) {
    document.querySelectorAll('#projectView .tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('#projectView .tab-content').forEach(c => c.style.display = 'none');
    
    event.target.classList.add('active');
    document.getElementById(tabName).style.display = 'block';
}

// ============================================================================
// CLIENT MANAGEMENT
// ============================================================================

function loadClients() {
    fetch('/api/clients')
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                allClients = Object.entries(data.clients).map(([id, info]) => ({
                    client_id: id,
                    ...info
                }));
                displayClientList();
                document.getElementById('totalClients').textContent = allClients.length;
            }
        })
        .catch(err => console.error('Error loading clients:', err));
}

function displayClientList() {
    const list = document.getElementById('clientList');
    if (!allClients.length) {
        list.innerHTML = '<p style="text-align: center; color: #999;">No clients yet</p>';
        return;
    }

    list.innerHTML = allClients.map(client => `
        <div class="client-item" onclick="selectClient('${client.client_id}')">
            <strong>${client.client_id}</strong>
            <br><small>${client.metadata?.name || 'No name'}</small>
        </div>
    `).join('');
}

function filterClients() {
    const search = document.getElementById('clientSearch').value.toLowerCase();
    document.querySelectorAll('.client-item').forEach(item => {
        item.style.display = item.textContent.toLowerCase().includes(search) ? '' : 'none';
    });
}

function selectClient(clientId) {
    currentClient = allClients.find(c => c.client_id === clientId);
    
    document.getElementById('welcomeMessage').style.display = 'none';
    document.getElementById('projectView').style.display = 'none';
    document.getElementById('clientDetails').style.display = 'block';

    document.getElementById('clientName').textContent = currentClient.metadata?.name || clientId;
    document.getElementById('clientId').textContent = clientId;
    document.getElementById('clientTier').textContent = (currentClient.metadata?.tier || 'free').toUpperCase();
    document.getElementById('currentRuleset').textContent = currentClient.ruleset;
    document.getElementById('featureCount').textContent = currentClient.feature_count || 0;

    // Display features
    const featureList = document.getElementById('featureList');
    if (currentClient.features && currentClient.features.length) {
        featureList.innerHTML = currentClient.features.map(f => `
            <div class="feature-card enabled">
                <div class="feature-name">${f}</div>
                <span class="feature-status enabled">Enabled</span>
            </div>
        `).join('');
    } else {
        featureList.innerHTML = '<p>No features</p>';
    }

    // Update ruleset selector
    const rulesetSelect = document.getElementById('newRulesetSelect');
    rulesetSelect.innerHTML = allRulesets.map(r => 
        `<option value="${r.id || r.name}">${r.name}</option>`
    ).join('');
}

function createClient() {
    const clientId = document.getElementById('clientIdInput').value;
    const ruleset = document.getElementById('rulesetSelect').value;
    const tier = document.getElementById('tierSelect').value;

    if (!clientId || !ruleset) {
        alert('Please fill in all fields');
        return;
    }

    fetch('/api/client', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            client_id: clientId,
            ruleset: ruleset,
            metadata: { tier: tier }
        })
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            alert('✅ Client created!');
            closeModal('createClientModal');
            loadClients();
            clearForm('clientIdInput', 'tierSelect');
        } else {
            alert('❌ Error: ' + data.error);
        }
    });
}

function deleteClient() {
    if (!confirm('Delete this client?')) return;
    alert('Delete functionality would be implemented with backend support');
}

function showChangeRulesetModal() {
    document.getElementById('changeRulesetModal').classList.add('active');
}

function changeClientRuleset() {
    const newRuleset = document.getElementById('newRulesetSelect').value;

    fetch(`/api/client/${currentClient.client_id}/ruleset`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ruleset: newRuleset })
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            alert('✅ Ruleset updated!');
            closeModal('changeRulesetModal');
            loadClients();
        } else {
            alert('❌ Error: ' + data.error);
        }
    });
}

// ============================================================================
// RULESET MANAGEMENT
// ============================================================================

function loadRulesets() {
    fetch('/api/rulesets')
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                allRulesets = data.rulesets || [];
                updateRulesetSelects();
                document.getElementById('totalRulesets').textContent = allRulesets.length;
                displayRulesets();
            }
        })
        .catch(err => console.error('Error loading rulesets:', err));
}

function updateRulesetSelects() {
    const selects = document.querySelectorAll('#rulesetSelect, #newRulesetSelect');
    selects.forEach(select => {
        const current = select.value;
        select.innerHTML = '<option value="">Select ruleset...</option>' +
            allRulesets.map(r => 
                `<option value="${r.id || r.name}">${r.name}</option>`
            ).join('');
        if (current) select.value = current;
    });
}

function displayRulesets() {
    const list = document.getElementById('rulesetsList');
    if (!allRulesets.length) {
        list.innerHTML = '<p>No rulesets yet</p>';
        return;
    }

    list.innerHTML = allRulesets.map(r => `
        <div class="feature-card">
            <div class="feature-name">${r.name}</div>
            <p style="font-size: 12px; color: #666; margin: 8px 0;">${r.description || 'No description'}</p>
            <p style="font-size: 11px;">
                Features: ${Array.isArray(r.features) ? r.features.length : 0}
            </p>
            <button class="btn btn-sm btn-secondary" onclick="deleteRuleset('${r.id || r.name}')">Delete</button>
        </div>
    `).join('');
}

function createRuleset() {
    const name = document.getElementById('rulesetNameInput').value;
    const desc = document.getElementById('rulesetDescInput').value;
    const rollout = parseInt(document.getElementById('rolloutPercentage').value) || 100;
    const features = document.getElementById('rulesetFeaturesInput').value
        .split(',')
        .map(f => f.trim())
        .filter(f => f);

    if (!name) {
        alert('Please enter a ruleset name');
        return;
    }

    fetch('/api/rulesets', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            name: name,
            description: desc,
            features: features,
            rollout_percentage: rollout
        })
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            alert('✅ Ruleset created!');
            document.getElementById('rulesetNameInput').value = '';
            document.getElementById('rulesetDescInput').value = '';
            document.getElementById('rulesetFeaturesInput').value = '';
            loadRulesets();
        } else {
            alert('❌ Error: ' + data.error);
        }
    });
}

function deleteRuleset(rulesetId) {
    if (!confirm('Delete this ruleset?')) return;

    fetch(`/api/rulesets/${rulesetId}`, {
        method: 'DELETE'
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            alert('✅ Ruleset deleted!');
            loadRulesets();
        } else {
            alert('❌ Error: ' + data.error);
        }
    });
}

function switchRulesetTab(tabName) {
    document.querySelectorAll('#rulesetBuilderModal .tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('#rulesetBuilderModal .tab-content').forEach(c => c.style.display = 'none');
    
    event.target.classList.add('active');
    document.getElementById(tabName).style.display = 'block';
    
    if (tabName === 'manage') {
        loadRulesets();
    }
}

// ============================================================================
// KILL SWITCH
// ============================================================================

function toggleKillSwitch() {
    const isActive = document.getElementById('killSwitch').checked;

    fetch('/api/kill-switch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ activate: isActive })
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            document.getElementById('killSwitchLabel').textContent = isActive ? 'Kill Switch: ON' : 'Kill Switch: OFF';
            document.getElementById('killSwitchStatus').textContent = isActive ? 'ON' : 'OFF';
        }
    });
}

function updateKillSwitchStatus() {
    fetch('/api/kill-switch')
        .then(r => r.json())
        .then(data => {
            if (data.success) {
                document.getElementById('killSwitch').checked = data.active;
                document.getElementById('killSwitchLabel').textContent = data.active ? 'Kill Switch: ON' : 'Kill Switch: OFF';
                document.getElementById('killSwitchStatus').textContent = data.active ? 'ON' : 'OFF';
            }
        });
}

// ============================================================================
// MODALS
// ============================================================================

function showCreateProjectModal() {
    document.getElementById('createProjectModal').classList.add('active');
}

function showCreateClientModal() {
    document.getElementById('createClientModal').classList.add('active');
    loadRulesets();
}

function showRulesetBuilder() {
    document.getElementById('rulesetBuilderModal').classList.add('active');
    loadRulesets();
}

function closeModal(modalId) {
    document.getElementById(modalId).classList.remove('active');
}

function createProject() {
    const name = document.getElementById('projectNameInput').value;
    const desc = document.getElementById('projectDescInput').value;
    const repo = document.getElementById('projectRepoInput').value;

    if (!name) {
        alert('Please enter a project name');
        return;
    }

    fetch('/api/projects', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            name: name,
            description: desc,
            repository_url: repo
        })
    })
    .then(r => r.json())
    .then(data => {
        if (data.success) {
            alert('✅ Project created!');
            closeModal('createProjectModal');
            loadProjects();
            document.getElementById('projectNameInput').value = '';
            document.getElementById('projectDescInput').value = '';
            document.getElementById('projectRepoInput').value = '';
        } else {
            alert('❌ Error: ' + data.error);
        }
    });
}

function clearForm(...inputIds) {
    inputIds.forEach(id => {
        const elem = document.getElementById(id);
        if (elem) elem.value = '';
    });
}
