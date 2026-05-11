/**
 * Full Potential Projects Dashboard - Frontend Logic
 */

// =============================================================================
// State
// =============================================================================

let projects = [];
let learnings = [];

// =============================================================================
// API Functions
// =============================================================================

async function fetchSummary() {
    try {
        const response = await fetch('/projects/api/summary');
        const data = await response.json();
        return data;
    } catch (error) {
        console.error('Error fetching summary:', error);
        return null;
    }
}

async function fetchProjects() {
    try {
        const response = await fetch('/projects/api/projects');
        projects = await response.json();
        return projects;
    } catch (error) {
        console.error('Error fetching projects:', error);
        return [];
    }
}

async function fetchLearnings() {
    try {
        const response = await fetch('/projects/api/memory');
        learnings = await response.json();
        return learnings;
    } catch (error) {
        console.error('Error fetching learnings:', error);
        return [];
    }
}

async function fetchActivity() {
    try {
        const response = await fetch('/projects/api/activity');
        return await response.json();
    } catch (error) {
        console.error('Error fetching activity:', error);
        return [];
    }
}

// =============================================================================
// Render Functions
// =============================================================================

function renderStats(summary) {
    document.getElementById('total-projects').textContent = summary.total_projects || 0;
    document.getElementById('active-projects').textContent = summary.active_projects || 0;
    document.getElementById('total-learnings').textContent = summary.recent_learnings?.length || 0;
}

function renderProjects(projectsList) {
    const container = document.getElementById('projects-grid');
    
    if (!projectsList || projectsList.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">📁</div>
                <p>No projects yet. Create your first project!</p>
            </div>
        `;
        return;
    }
    
    container.innerHTML = projectsList.map(p => {
        const project = p.project || p;
        const live = p.live || p.live_status;
        const online = p.online;
        
        // Extract metrics from live status
        let metrics = '';
        if (live && live.metrics) {
            const m = live.metrics;
            metrics = `
                <div class="project-metrics">
                    <div class="project-metric">
                        <div class="project-metric-value">${m.miami_builders || 0}/${m.miami_builders_needed || 5}</div>
                        <div class="project-metric-label">Miami</div>
                    </div>
                    <div class="project-metric">
                        <div class="project-metric-value">${m.china_contacts || 0}/${m.china_contacts_needed || 3}</div>
                        <div class="project-metric-label">China</div>
                    </div>
                    <div class="project-metric">
                        <div class="project-metric-value">${m.tasks_completed || 0}/${m.tasks_total || 0}</div>
                        <div class="project-metric-label">Tasks</div>
                    </div>
                </div>
            `;
        }
        
        return `
            <div class="project-card" style="--project-color: ${project.color || '#8b5cf6'}" onclick="openProject('${project.id}')">
                <div class="project-header">
                    <div class="project-icon">${project.icon || '📁'}</div>
                    <div class="project-info">
                        <h3>${project.name}</h3>
                        <div class="project-status ${online ? 'online' : 'offline'}">
                            <span class="status-dot"></span>
                            ${online ? 'Online' : 'Offline'}
                        </div>
                    </div>
                </div>
                <p class="project-description">${project.description || 'No description'}</p>
                ${metrics}
            </div>
        `;
    }).join('');
}

function renderLearnings(learningsList) {
    const container = document.getElementById('memory-list');
    
    if (!learningsList || learningsList.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">🧠</div>
                <p>No learnings yet. Add your first insight!</p>
            </div>
        `;
        return;
    }
    
    container.innerHTML = learningsList.map(l => `
        <div class="memory-item">
            <div>
                <span class="memory-category">${l.category}</span>
                <div class="memory-text">${l.learning}</div>
                ${l.context ? `<div class="memory-context">📍 ${l.context}</div>` : ''}
            </div>
        </div>
    `).join('');
}

function renderActivity(activityList) {
    const container = document.getElementById('activity-list');
    
    if (!activityList || activityList.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <p>No activity yet</p>
            </div>
        `;
        return;
    }
    
    const icons = {
        'builder_added': '➕',
        'task_completed': '✅',
        'joined': '👋',
        'learning_added': '🧠'
    };
    
    container.innerHTML = activityList.map(a => `
        <div class="activity-item">
            <span class="activity-icon">${icons[a.action] || '📌'}</span>
            <div class="activity-content">
                ${a.project_name ? `<span class="activity-project">${a.project_name}</span>` : ''}
                <div class="activity-text">${a.details || a.action}</div>
            </div>
            <span class="activity-time">${formatTimeAgo(a.created_at)}</span>
        </div>
    `).join('');
}

function formatTimeAgo(timestamp) {
    if (!timestamp) return '';
    const now = new Date();
    const then = new Date(timestamp);
    const diff = Math.floor((now - then) / 1000 / 60);
    
    if (diff < 1) return 'just now';
    if (diff < 60) return `${diff}m ago`;
    if (diff < 1440) return `${Math.floor(diff / 60)}h ago`;
    return `${Math.floor(diff / 1440)}d ago`;
}

// =============================================================================
// Actions
// =============================================================================

function openProject(projectId) {
    window.location.href = `/projects/${projectId}/`;
}

function showNewProjectModal() {
    document.getElementById('new-project-modal').classList.remove('hidden');
}

function showAddLearningModal() {
    // Populate projects dropdown
    const select = document.getElementById('learning-project-select');
    select.innerHTML = '<option value="">Global (applies to all)</option>' +
        projects.map(p => {
            const project = p.project || p;
            return `<option value="${project.id}">${project.name}</option>`;
        }).join('');
    
    document.getElementById('add-learning-modal').classList.remove('hidden');
}

function closeModal(modalId) {
    document.getElementById(modalId).classList.add('hidden');
}

async function createProject(event) {
    event.preventDefault();
    const form = event.target;
    
    const data = {
        id: form.querySelector('[name="id"]').value,
        name: form.querySelector('[name="name"]').value,
        description: form.querySelector('[name="description"]').value,
        icon: form.querySelector('[name="icon"]').value,
        color: form.querySelector('[name="color"]').value
    };
    
    try {
        const response = await fetch('/projects/api/projects', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        
        if (response.ok) {
            closeModal('new-project-modal');
            form.reset();
            await loadDashboard();
            showToast('Project created!', 'success');
        } else {
            showToast('Error creating project', 'error');
        }
    } catch (error) {
        console.error('Error:', error);
        showToast('Error creating project', 'error');
    }
}

async function addLearning(event) {
    event.preventDefault();
    const form = event.target;
    
    const data = {
        project_id: form.querySelector('[name="project_id"]').value || null,
        category: form.querySelector('[name="category"]').value,
        learning: form.querySelector('[name="learning"]').value,
        context: form.querySelector('[name="context"]').value || null
    };
    
    try {
        const response = await fetch('/projects/api/memory', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        
        if (response.ok) {
            closeModal('add-learning-modal');
            form.reset();
            const newLearnings = await fetchLearnings();
            renderLearnings(newLearnings);
            showToast('Learning saved!', 'success');
        } else {
            showToast('Error saving learning', 'error');
        }
    } catch (error) {
        console.error('Error:', error);
        showToast('Error saving learning', 'error');
    }
}

// =============================================================================
// Brain Chat
// =============================================================================

let brainOpen = false;

function toggleBrainChat() {
    brainOpen = !brainOpen;
    const panel = document.getElementById('brain-panel');
    
    if (brainOpen) {
        panel.classList.remove('hidden');
        document.getElementById('brain-input').focus();
    } else {
        panel.classList.add('hidden');
    }
}

async function sendBrainMessage(event) {
    event.preventDefault();
    
    const input = document.getElementById('brain-input');
    const message = input.value.trim();
    if (!message) return;
    
    // Add user message
    addBrainMessage(message, 'user');
    input.value = '';
    
    // Show typing indicator
    const typingId = addTypingIndicator();
    
    try {
        const response = await fetch('/projects/api/brain/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message })
        });
        
        const data = await response.json();
        removeTypingIndicator(typingId);
        addBrainMessage(data.response, 'ai');
        
    } catch (error) {
        console.error('Brain error:', error);
        removeTypingIndicator(typingId);
        addBrainMessage('Sorry, I had trouble processing that. Try again!', 'ai');
    }
}

function addBrainMessage(content, type) {
    const container = document.getElementById('brain-messages');
    const div = document.createElement('div');
    div.className = `brain-message ${type}`;
    div.textContent = content;
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
}

function addTypingIndicator() {
    const container = document.getElementById('brain-messages');
    const div = document.createElement('div');
    const id = 'typing-' + Date.now();
    div.id = id;
    div.className = 'brain-message ai';
    div.innerHTML = '<span class="typing">Thinking...</span>';
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
    return id;
}

function removeTypingIndicator(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
}

// =============================================================================
// Toast Notifications
// =============================================================================

function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    toast.style.cssText = `
        position: fixed;
        bottom: 2rem;
        left: 50%;
        transform: translateX(-50%);
        padding: 1rem 2rem;
        background: ${type === 'success' ? '#10b981' : type === 'error' ? '#ef4444' : '#3b82f6'};
        color: white;
        border-radius: 8px;
        font-weight: 500;
        z-index: 9999;
        animation: slideUp 0.3s ease-out;
    `;
    document.body.appendChild(toast);
    
    setTimeout(() => {
        toast.remove();
    }, 3000);
}

// =============================================================================
// Initialize
// =============================================================================

async function loadDashboard() {
    const summary = await fetchSummary();
    
    if (summary) {
        renderStats(summary);
        renderProjects(summary.projects);
        renderLearnings(summary.recent_learnings);
        renderActivity(summary.recent_activity);
    } else {
        // Fallback to individual fetches
        const projectsList = await fetchProjects();
        renderProjects(projectsList);
        
        const learningsList = await fetchLearnings();
        renderLearnings(learningsList);
        
        const activityList = await fetchActivity();
        renderActivity(activityList);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    loadDashboard();
    
    // Refresh every 60 seconds
    setInterval(loadDashboard, 60000);
    
    // Close modals on escape
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            document.querySelectorAll('.modal:not(.hidden)').forEach(m => m.classList.add('hidden'));
            if (brainOpen) toggleBrainChat();
        }
    });
});

