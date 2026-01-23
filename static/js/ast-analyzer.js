// AST Analysis and Function Graph Visualization

let currentProject = null;
let functionGraph = null;

// Initialize AST analyzer features
function initASTAnalyzer() {
    loadProjects();
    setupASTEventListeners();
}

function setupASTEventListeners() {
    // Project selection
    const projectSelect = document.getElementById('projectSelect');
    if (projectSelect) {
        projectSelect.addEventListener('change', onProjectSelected);
    }

    // Analyze code button
    const analyzeBtn = document.getElementById('analyzeCodeBtn');
    if (analyzeBtn) {
        analyzeBtn.addEventListener('click', openAnalyzeModal);
    }

    // Create project button
    const createProjectBtn = document.getElementById('createProjectBtn');
    if (createProjectBtn) {
        createProjectBtn.addEventListener('click', openCreateProjectModal);
    }
}

// Load all projects
async function loadProjects() {
    try {
        const response = await fetch('/api/projects');
        const data = await response.json();

        if (data.success) {
            renderProjectsList(data.projects);
        }
    } catch (error) {
        console.error('Error loading projects:', error);
    }
}

// Render projects dropdown
function renderProjectsList(projects) {
    const projectSelect = document.getElementById('projectSelect');
    if (!projectSelect) return;

    projectSelect.innerHTML = '<option value="">Select a project...</option>';

    projects.forEach(project => {
        const option = document.createElement('option');
        option.value = project.id;
        option.textContent = project.name;
        projectSelect.appendChild(option);
    });

    const totalProjectsEl = document.getElementById('totalProjects');
    if (totalProjectsEl) {
        totalProjectsEl.textContent = projects.length;
    }
}

// Handle project selection
async function onProjectSelected(event) {
    const projectId = event.target.value;
    if (!projectId) {
        currentProject = null;
        return;
    }

    try {
        const response = await fetch(`/api/projects/${projectId}`);
        const data = await response.json();

        if (data.success) {
            currentProject = data.project;
            loadProjectData(projectId);
        }
    } catch (error) {
        console.error('Error loading project:', error);
    }
}

// Load all data for selected project
async function loadProjectData(projectId) {
    await Promise.all([
        loadProjectFunctions(projectId),
        loadProjectFeatures(projectId)
    ]);
}

// Load functions for a project
async function loadProjectFunctions(projectId) {
    try {
        const response = await fetch(`/api/projects/${projectId}/functions`);
        const data = await response.json();

        if (data.success) {
            renderFunctionsList(data.functions);
        }
    } catch (error) {
        console.error('Error loading functions:', error);
    }
}

// Render functions list
function renderFunctionsList(functions) {
    const container = document.getElementById('functionsList');
    if (!container) return;

    if (functions.length === 0) {
        container.innerHTML = '<p class="empty-state">No functions analyzed yet. Upload code to analyze.</p>';
        return;
    }

    // Group functions by type
    const flagged = functions.filter(f => f.is_feature_flagged);
    const helpers = functions.filter(f => f.is_helper && !f.is_feature_flagged);
    const shared = functions.filter(f => f.is_shared_helper);
    const regular = functions.filter(f => !f.is_feature_flagged && !f.is_helper);

    let html = '<div class="functions-groups">';

    if (flagged.length > 0) {
        html += '<div class="function-group">';
        html += '<h3>🚩 Feature-Flagged Functions</h3>';
        flagged.forEach(func => {
            html += renderFunctionCard(func, 'flagged');
        });
        html += '</div>';
    }

    if (shared.length > 0) {
        html += '<div class="function-group">';
        html += '<h3>🔗 Shared Helpers</h3>';
        shared.forEach(func => {
            html += renderFunctionCard(func, 'shared');
        });
        html += '</div>';
    }

    if (helpers.length > 0) {
        html += '<div class="function-group">';
        html += '<h3>🔧 Helper Functions</h3>';
        helpers.forEach(func => {
            html += renderFunctionCard(func, 'helper');
        });
        html += '</div>';
    }

    if (regular.length > 0) {
        html += '<div class="function-group">';
        html += '<h3>📦 Regular Functions</h3>';
        regular.forEach(func => {
            html += renderFunctionCard(func, 'regular');
        });
        html += '</div>';
    }

    html += '</div>';
    container.innerHTML = html;
}

// Render individual function card
function renderFunctionCard(func, type) {
    const badges = [];
    if (func.is_feature_flagged) badges.push('<span class="badge badge-feature">Feature</span>');
    if (func.is_shared_helper) badges.push('<span class="badge badge-shared">Shared</span>');
    if (func.is_helper && !func.is_shared_helper) badges.push('<span class="badge badge-helper">Helper</span>');

    return `
        <div class="function-card ${type}">
            <div class="function-header">
                <strong>${func.function_name}</strong>
                <span class="complexity">Complexity: ${func.complexity_score || 0}</span>
            </div>
            <div class="function-meta">
                <span class="file-path">${func.file_path}:${func.line_number || '?'}</span>
            </div>
            <div class="function-badges">
                ${badges.join(' ')}
            </div>
        </div>
    `;
}

// Load features for a project
async function loadProjectFeatures(projectId) {
    try {
        const response = await fetch(`/api/projects/${projectId}/features`);
        const data = await response.json();

        if (data.success) {
            renderFeaturesList(data.features);
        }
    } catch (error) {
        console.error('Error loading features:', error);
    }
}

// Render features list with impact analysis
function renderFeaturesList(features) {
    const container = document.getElementById('featuresList');
    if (!container) return;

    if (features.length === 0) {
        container.innerHTML = '<p class="empty-state">No features found.</p>';
        return;
    }

    let html = '<div class="features-grid">';

    features.forEach(feature => {
        html += `
            <div class="feature-card" data-feature-id="${feature.id}">
                <div class="feature-header">
                    <h3>${feature.feature_name}</h3>
                    <label class="switch">
                        <input type="checkbox" ${feature.is_enabled ? 'checked' : ''}
                               onchange="toggleFeature('${feature.id}', this.checked)">
                        <span class="slider"></span>
                    </label>
                </div>
                <p class="feature-description">${feature.description || 'No description'}</p>
                <button class="btn btn-sm" onclick="viewFeatureImpact('${feature.id}')">
                    View Impact Analysis
                </button>
            </div>
        `;
    });

    html += '</div>';
    container.innerHTML = html;
}

// Toggle feature on/off
async function toggleFeature(featureId, enabled) {
    try {
        const response = await fetch(`/api/features/${featureId}/toggle`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ is_enabled: enabled })
        });

        const data = await response.json();
        if (data.success) {
            showNotification(`Feature ${enabled ? 'enabled' : 'disabled'} successfully`);
        } else {
            showNotification('Error toggling feature', 'error');
        }
    } catch (error) {
        console.error('Error toggling feature:', error);
        showNotification('Error toggling feature', 'error');
    }
}

// View feature impact analysis
async function viewFeatureImpact(featureId) {
    try {
        const response = await fetch(`/api/features/${featureId}/impact`);
        const data = await response.json();

        if (data.success) {
            displayImpactAnalysis(data.impact);
        } else {
            showNotification('No impact analysis available', 'warning');
        }
    } catch (error) {
        console.error('Error loading impact analysis:', error);
        showNotification('Error loading impact analysis', 'error');
    }
}

// Display impact analysis modal
function displayImpactAnalysis(impact) {
    const modal = document.getElementById('impactModal');
    if (!modal) return;

    const content = document.getElementById('impactContent');
    const analysisData = impact.analysis_data;

    let html = `
        <div class="impact-summary">
            <h3>Impact Summary</h3>
            <div class="stats-grid">
                <div class="stat-card">
                    <h4>${impact.total_affected_functions}</h4>
                    <p>Total Affected</p>
                </div>
                <div class="stat-card">
                    <h4>${impact.functions_unreachable}</h4>
                    <p>Can Disable</p>
                </div>
                <div class="stat-card">
                    <h4>${impact.functions_need_fallback}</h4>
                    <p>Need Fallback</p>
                </div>
            </div>
        </div>

        <div class="impact-details">
            <h3>Detailed Analysis</h3>
            <pre>${JSON.stringify(analysisData, null, 2)}</pre>
        </div>
    `;

    content.innerHTML = html;
    modal.style.display = 'block';
}

// Create new project
async function createProject(name, description, repositoryUrl) {
    try {
        const response = await fetch('/api/projects', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                name,
                description,
                repository_url: repositoryUrl
            })
        });

        const data = await response.json();
        if (data.success) {
            showNotification('Project created successfully');
            loadProjects();
            return data.project;
        } else {
            showNotification(data.error || 'Error creating project', 'error');
        }
    } catch (error) {
        console.error('Error creating project:', error);
        showNotification('Error creating project', 'error');
    }
}

// Analyze code
async function analyzeCode(projectId, filePath, fileContent) {
    try {
        const response = await fetch('/api/analyze', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                project_id: projectId,
                file_path: filePath,
                file_content: fileContent ? btoa(fileContent) : null
            })
        });

        const data = await response.json();
        if (data.success) {
            showNotification('Code analyzed successfully');
            loadProjectData(projectId);
            return data.analysis;
        } else {
            showNotification(data.error || 'Error analyzing code', 'error');
        }
    } catch (error) {
        console.error('Error analyzing code:', error);
        showNotification('Error analyzing code', 'error');
    }
}

// Show notification
function showNotification(message, type = 'success') {
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;
    document.body.appendChild(notification);

    setTimeout(() => {
        notification.classList.add('show');
    }, 100);

    setTimeout(() => {
        notification.classList.remove('show');
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

// Modal helpers
function openAnalyzeModal() {
    const modal = document.getElementById('analyzeModal');
    if (modal) modal.style.display = 'block';
}

function openCreateProjectModal() {
    const modal = document.getElementById('createProjectModal');
    if (modal) modal.style.display = 'block';
}

function closeModals() {
    document.querySelectorAll('.modal').forEach(modal => {
        modal.style.display = 'none';
    });
}

// Initialize on page load
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initASTAnalyzer);
} else {
    initASTAnalyzer();
}
