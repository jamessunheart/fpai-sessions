/**
 * COCOON Command Center - Frontend Logic
 * Multi-assistant collaborative project execution
 */

// =============================================================================
// State
// =============================================================================

let currentLocation = 'Miami';
let builders = [];
let tasks = [];
let clockedIn = false;
let currentMessageType = null;

// Assistant tracking
let currentAssistant = null;  // { id, name }

// =============================================================================
// Assistant Registration
// =============================================================================

async function checkAssistant() {
    // Check if assistant is already registered in this session
    const stored = localStorage.getItem('cocoon_assistant');
    if (stored) {
        currentAssistant = JSON.parse(stored);
        updateAssistantDisplay();
        return;
    }
    // Show registration modal
    showAssistantModal();
}

function showAssistantModal() {
    document.getElementById('assistant-modal').classList.remove('hidden');
    document.getElementById('assistant-name-input').focus();
}

async function registerAssistant(event) {
    event.preventDefault();
    const name = document.getElementById('assistant-name-input').value.trim();
    const email = document.getElementById('assistant-email-input').value.trim();
    
    if (!name) {
        showToast('Please enter your name', 'error');
        return;
    }
    
    try {
        const response = await fetch('/projects/cocoon/api/assistants/register', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, email: email || null })
        });
        const data = await response.json();
        
        currentAssistant = { id: data.id, name: data.name };
        localStorage.setItem('cocoon_assistant', JSON.stringify(currentAssistant));
        
        document.getElementById('assistant-modal').classList.add('hidden');
        updateAssistantDisplay();
        showToast(data.message, 'success');
        
        // Load activity feed
        loadActivityFeed();
    } catch (error) {
        console.error('Registration error:', error);
        showToast('Error registering', 'error');
    }
}

function updateAssistantDisplay() {
    const badge = document.getElementById('assistant-badge');
    if (badge && currentAssistant) {
        badge.textContent = currentAssistant.name;
        badge.style.display = 'inline-block';
    }
}

function changeAssistant() {
    localStorage.removeItem('cocoon_assistant');
    currentAssistant = null;
    showAssistantModal();
}

// =============================================================================
// Activity Feed
// =============================================================================

async function loadActivityFeed() {
    try {
        const response = await fetch('/projects/cocoon/api/activity?limit=10');
        const activities = await response.json();
        renderActivityFeed(activities);
    } catch (error) {
        console.error('Error loading activity:', error);
    }
}

function renderActivityFeed(activities) {
    const container = document.getElementById('activity-feed');
    if (!container) return;
    
    if (activities.length === 0) {
        container.innerHTML = '<div class="activity-empty">No activity yet. Be the first!</div>';
        return;
    }
    
    container.innerHTML = activities.map(a => {
        const icon = getActivityIcon(a.action);
        const time = formatTimeAgo(a.created_at);
        return `
            <div class="activity-item">
                <span class="activity-icon">${icon}</span>
                <div class="activity-content">
                    <span class="activity-name">${a.assistant_name || 'Someone'}</span>
                    <span class="activity-details">${a.details || a.action}</span>
                </div>
                <span class="activity-time">${time}</span>
            </div>
        `;
    }).join('');
}

function getActivityIcon(action) {
    const icons = {
        'joined': '👋',
        'added_builder': '➕',
        'completed_task': '✅',
        'clocked_in': '⏱️',
        'clocked_out': '🏁',
        'submitted_report': '📋'
    };
    return icons[action] || '📌';
}

function formatTimeAgo(timestamp) {
    const now = new Date();
    const then = new Date(timestamp);
    const diff = Math.floor((now - then) / 1000 / 60); // minutes
    
    if (diff < 1) return 'just now';
    if (diff < 60) return `${diff}m ago`;
    if (diff < 1440) return `${Math.floor(diff / 60)}h ago`;
    return `${Math.floor(diff / 1440)}d ago`;
}

async function loadActiveAssistants() {
    try {
        const response = await fetch('/projects/cocoon/api/assistants/active');
        const active = await response.json();
        renderActiveAssistants(active);
    } catch (error) {
        console.error('Error loading active assistants:', error);
    }
}

function renderActiveAssistants(assistants) {
    const container = document.getElementById('active-assistants');
    if (!container) return;
    
    if (assistants.length === 0) {
        container.innerHTML = '<span class="no-active">No one online</span>';
        return;
    }
    
    container.innerHTML = assistants.map(a => 
        `<span class="active-dot">🟢 ${a.name}</span>`
    ).join(' ');
}

// =============================================================================
// Brain (AI Guidance)
// =============================================================================

async function getBrainGuidance(eventType, details = {}) {
    try {
        const response = await fetch('/projects/cocoon/api/brain/event', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ event_type: eventType, details })
        });
        const data = await response.json();
        
        // Show the guidance
        showBrainGuidance(data.guidance, data.notifications);
        
        return data;
    } catch (error) {
        console.error('Brain error:', error);
    }
}

async function askBrain(question) {
    try {
        const response = await fetch('/projects/cocoon/api/brain/ask', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                question, 
                assistant_name: currentAssistant?.name 
            })
        });
        const data = await response.json();
        showBrainGuidance(data.answer);
        return data.answer;
    } catch (error) {
        console.error('Brain ask error:', error);
        return null;
    }
}

async function getNextStep() {
    try {
        const response = await fetch(`/projects/cocoon/api/brain/next-step?assistant_name=${currentAssistant?.name || ''}`);
        const data = await response.json();
        showBrainGuidance(data.guidance);
        updatePhaseDisplay(data.phase);
        return data;
    } catch (error) {
        console.error('Next step error:', error);
    }
}

function showBrainGuidance(guidance, notifications = []) {
    // Remove existing guidance
    const existing = document.getElementById('brain-guidance');
    if (existing) existing.remove();
    
    // Create guidance panel
    const panel = document.createElement('div');
    panel.id = 'brain-guidance';
    panel.className = 'brain-guidance';
    panel.innerHTML = `
        <div class="brain-header">
            <span class="brain-icon">🧠</span>
            <span class="brain-title">AI Brain says:</span>
            <button class="brain-close" onclick="closeBrainGuidance()">×</button>
        </div>
        <div class="brain-message">${guidance}</div>
        ${notifications.length > 0 ? `
            <div class="brain-notifications">
                ${notifications.map(n => `<div class="brain-notification">🎉 ${n}</div>`).join('')}
            </div>
        ` : ''}
    `;
    
    document.body.appendChild(panel);
    
    // Auto-hide after 15 seconds
    setTimeout(() => {
        closeBrainGuidance();
    }, 15000);
}

function closeBrainGuidance() {
    const panel = document.getElementById('brain-guidance');
    if (panel) {
        panel.classList.add('hiding');
        setTimeout(() => panel.remove(), 300);
    }
}

function updatePhaseDisplay(phase) {
    const phaseDisplay = document.getElementById('current-phase');
    if (phaseDisplay) {
        phaseDisplay.textContent = phase;
    }
}

async function loadBrainStatus() {
    try {
        const response = await fetch('/projects/cocoon/api/brain/status');
        const data = await response.json();
        
        if (data.current_phase) {
            updatePhaseDisplay(data.current_phase.name);
        }
    } catch (error) {
        console.error('Brain status error:', error);
    }
}

// =============================================================================
// AI Chat Widget
// =============================================================================

let chatOpen = false;

function toggleChat() {
    const panel = document.getElementById('chat-panel');
    const toggle = document.querySelector('.chat-toggle');
    chatOpen = !chatOpen;
    
    if (chatOpen) {
        panel.classList.remove('hidden');
        toggle.classList.add('active');
        document.getElementById('chat-input').focus();
    } else {
        panel.classList.add('hidden');
        toggle.classList.remove('active');
    }
}

async function sendChatMessage(event) {
    event.preventDefault();
    
    const input = document.getElementById('chat-input');
    const message = input.value.trim();
    
    if (!message) return;
    
    // Add user message to chat
    addChatMessage(message, 'user');
    input.value = '';
    
    // Show typing indicator
    const typingId = addTypingIndicator();
    
    try {
        const response = await fetch('/projects/cocoon/api/brain/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: message,
                assistant_name: currentAssistant?.name || null
            })
        });
        
        const data = await response.json();
        
        // Remove typing indicator
        removeTypingIndicator(typingId);
        
        // Add AI response
        addChatMessage(data.response, 'ai');
        
    } catch (error) {
        console.error('Chat error:', error);
        removeTypingIndicator(typingId);
        addChatMessage("Sorry, I had trouble processing that. Try again!", 'ai');
    }
}

function addChatMessage(content, type) {
    const container = document.getElementById('chat-messages');
    const messageDiv = document.createElement('div');
    messageDiv.className = `chat-message ${type}`;
    messageDiv.innerHTML = `<div class="chat-bubble">${escapeHtml(content)}</div>`;
    container.appendChild(messageDiv);
    container.scrollTop = container.scrollHeight;
}

function addTypingIndicator() {
    const container = document.getElementById('chat-messages');
    const typingDiv = document.createElement('div');
    const typingId = 'typing-' + Date.now();
    typingDiv.id = typingId;
    typingDiv.className = 'chat-message ai typing';
    typingDiv.innerHTML = `
        <div class="chat-bubble">
            <span class="typing-dots">
                <span></span><span></span><span></span>
            </span>
        </div>
    `;
    container.appendChild(typingDiv);
    container.scrollTop = container.scrollHeight;
    return typingId;
}

function removeTypingIndicator(typingId) {
    const typing = document.getElementById(typingId);
    if (typing) typing.remove();
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Quick questions for the chat
function askQuickQuestion(question) {
    document.getElementById('chat-input').value = question;
    if (!chatOpen) toggleChat();
    setTimeout(() => {
        document.querySelector('.chat-input-form').dispatchEvent(new Event('submit'));
    }, 100);
}

// =============================================================================
// Outreach Messages (Verbatim - Do Not Edit)
// =============================================================================

const MESSAGES = {
    miami: {
        title: 'Miami Outreach',
        content: `Hi — I'm coordinating a prototype build in Miami.

We're looking to fabricate a one-person recovery cocoon — a soft enclosure that goes over a person lying on a mat.

Inside is diffused LED lighting (off-the-shelf components).

This is not medical equipment and does not require electronics design.

We need one fast prototype and want to understand:
• whether this is something you can build
• rough cost range
• rough timeline
• materials you'd recommend

Happy to share a short spec or image if helpful.`
    },
    china: {
        title: 'China Outreach',
        content: `Hi — I'm exploring manufacturing options for a wellness product.

We're developing a one-person recovery cocoon — a soft enclosure that goes over a person lying on a mat. Think of it as a fabric/inflatable structure with integrated LED lighting.

This is not medical equipment. It uses off-the-shelf LED components.

We're looking for:
• rough unit cost at MOQ 10, 50, 100
• estimated production timeline
• material recommendations (inflatable vs fabric-framed)
• your experience with similar soft-goods or enclosure products

We have a prototype being built locally first, then will move to manufacturing. Happy to share specs.`
    },
    followup: {
        title: 'Follow-up Message',
        content: `Hi — just following up on my message about the recovery cocoon prototype.

Would love to know if this is something you can help with, or if you can point me to someone who might be a better fit.

Thanks!`
    },
    schedule: {
        title: 'Schedule Call',
        content: `Thanks for your response — this sounds promising.

Would you have 15-20 minutes this week for a quick call? I can share more details on the spec and answer any questions.

I'm flexible on timing — just let me know what works for you.`
    }
};

// =============================================================================
// API Functions
// =============================================================================

async function fetchStatus() {
    try {
        const response = await fetch('/projects/cocoon/api/status');
        const data = await response.json();
        return data;
    } catch (error) {
        console.error('Error fetching status:', error);
        return null;
    }
}

async function fetchBuilders() {
    try {
        const response = await fetch('/projects/cocoon/api/builders');
        builders = await response.json();
        return builders;
    } catch (error) {
        console.error('Error fetching builders:', error);
        return [];
    }
}

async function fetchTasks() {
    try {
        const response = await fetch('/projects/cocoon/api/tasks');
        tasks = await response.json();
        return tasks;
    } catch (error) {
        console.error('Error fetching tasks:', error);
        return [];
    }
}

// =============================================================================
// Render Functions
// =============================================================================

// Task helpers - show relevant tips/links for specific tasks
const TASK_HELPERS = {
    'Read ASSISTANT_SOP': {
        tip: '<a href="#sop-section" onclick="scrollToSection(\'sop-section\')">↓ Click here to read your SOP</a>',
        icon: '📋',
        isLink: true
    },
    'Open TRACKER': {
        tip: '<a href="#builder-tracker" onclick="scrollToSection(\'builder-tracker\')">↓ Click here to open the Builder Tracker</a>',
        icon: '🏗️',
        isLink: true
    },
    'Identify 5 Miami fabricators': {
        tip: '<a href="#find-builders" onclick="scrollToSection(\'find-builders\')">↓ Click here → Find Builders section</a>',
        icon: '🔍',
        isLink: true
    },
    'Identify 2-3 China sourcing contacts': {
        tip: '<a href="#find-builders" onclick="scrollToSection(\'find-builders\')">↓ Click here → Find Builders section (China links)</a>',
        icon: '🔍',
        isLink: true
    },
    'Add all 5 Miami fabricators to tracker': {
        tip: '<a href="#builder-tracker" onclick="scrollToSection(\'builder-tracker\')">↓ Click here → then click "+ Add Builder"</a>',
        icon: '➕',
        isLink: true
    },
    'Add all China contacts to tracker': {
        tip: '<a href="#builder-tracker" onclick="scrollToSection(\'builder-tracker\')">↓ Click here → then click "+ Add Builder"</a>',
        icon: '➕',
        isLink: true
    },
    'Copy Miami outreach message': {
        tip: '↓ Scroll to "Outreach Messages" and click "Miami Outreach"',
        icon: '📨'
    },
    'Copy China outreach message': {
        tip: '↓ Scroll to "Outreach Messages" and click "China Outreach"',
        icon: '📨'
    },
    'Send outreach to all 5 Miami fabricators': {
        tip: 'Copy message from Outreach section, paste to each builder\'s contact',
        icon: '✉️'
    },
    'Send outreach to all China contacts': {
        tip: 'Copy message from Outreach section, paste to each contact',
        icon: '✉️'
    },
    'Send follow-up to non-responders': {
        tip: '↓ Use the "Follow-up" message in Outreach Messages',
        icon: '🔄'
    },
    'Submit weekly report': {
        tip: '↓ Fill out the Weekly Report form at the bottom',
        icon: '📝'
    }
};

// Scroll to section smoothly
function scrollToSection(sectionId) {
    event.preventDefault();
    const section = document.getElementById(sectionId);
    if (section) {
        section.scrollIntoView({ behavior: 'smooth', block: 'start' });
        // If it's a details element, open it
        const details = section.closest('details') || section.querySelector('details');
        if (details) {
            details.open = true;
        }
        // Highlight briefly
        section.classList.add('highlight-section');
        setTimeout(() => section.classList.remove('highlight-section'), 2000);
    }
}

function getTaskHelper(description) {
    for (const [key, helper] of Object.entries(TASK_HELPERS)) {
        if (description.toLowerCase().includes(key.toLowerCase())) {
            return helper;
        }
    }
    return null;
}

function renderTodayTasks(tasks, currentDay) {
    const container = document.getElementById('today-tasks');
    const todayTasks = tasks.filter(t => t.day === currentDay);
    
    if (todayTasks.length === 0) {
        container.innerHTML = '<li class="task-item"><span class="task-label" style="color: var(--text-muted)">No tasks for today</span></li>';
        return;
    }
    
    container.innerHTML = todayTasks.map(task => {
        const helper = getTaskHelper(task.description);
        const helperHTML = helper && !task.completed 
            ? `<span class="task-helper"><span class="helper-icon">${helper.icon}</span> ${helper.tip}</span>`
            : '';
        
        const timeSpent = task.time_spent_minutes || 0;
        const timeHTML = task.completed 
            ? `<span class="task-time" onclick="openTimeEntryModal(${task.id}, ${timeSpent})" title="Click to edit time">
                <span class="time-icon">⏱</span> ${formatTime(timeSpent)}
               </span>`
            : '';
        
        return `
            <li class="task-item ${task.completed ? 'completed' : ''}">
                <input type="checkbox" class="task-checkbox" 
                       ${task.completed ? 'checked' : ''} 
                       onchange="toggleTask(${task.id}, this.checked, ${timeSpent})">
                <div class="task-content">
                    <label class="task-label">${task.description}</label>
                    ${helperHTML}
                    ${timeHTML}
                </div>
            </li>
        `;
    }).join('');
}

function renderMetrics(status) {
    const { builders, tasks, time } = status;
    
    // Progress
    document.getElementById('progress-percent').textContent = `${tasks.progress_percent}%`;
    document.getElementById('progress-fill').style.width = `${tasks.progress_percent}%`;
    
    // Metrics
    document.getElementById('metric-contacted').textContent = `${builders.contacted}/${builders.total}`;
    document.getElementById('metric-replied').textContent = builders.replied;
    document.getElementById('metric-calls').textContent = builders.calls_scheduled;
    
    // Task time (convert to hours if > 60 mins)
    const taskTimeMinutes = tasks.total_time_minutes || 0;
    const taskTimeDisplay = taskTimeMinutes >= 60 
        ? `${Math.floor(taskTimeMinutes / 60)}h ${taskTimeMinutes % 60}m`
        : `${taskTimeMinutes}m`;
    document.getElementById('metric-hours').textContent = taskTimeDisplay;
    
    // Clock status
    clockedIn = time.currently_clocked_in;
    updateClockButton();
    
    if (time.currently_clocked_in && time.active_session_start) {
        updateElapsedTime(time.active_session_start);
    }
}

function renderBuilders(builders, location) {
    const container = document.getElementById('tracker-body');
    const filtered = builders.filter(b => b.location === location);
    
    // Update counts
    const miamiCount = builders.filter(b => b.location === 'Miami').length;
    const chinaCount = builders.filter(b => b.location === 'China').length;
    
    document.getElementById('miami-count').textContent = miamiCount;
    document.getElementById('china-count').textContent = chinaCount;
    
    // Update hero progress counts
    const miamiProgress = document.getElementById('miami-progress');
    const chinaProgress = document.getElementById('china-progress');
    if (miamiProgress) miamiProgress.textContent = miamiCount;
    if (chinaProgress) chinaProgress.textContent = chinaCount;
    
    if (filtered.length === 0) {
        container.innerHTML = `
            <tr>
                <td colspan="6" class="empty-state">
                    No ${location} builders yet. Click "+ Add Builder" to add one.
                </td>
            </tr>
        `;
        return;
    }
    
    container.innerHTML = filtered.map(b => `
        <tr>
            <td>
                <strong>${b.name}</strong>
                ${b.contact ? `<br><small style="color: var(--text-muted)">${b.contact}</small>` : ''}
            </td>
            <td><span class="status-badge ${getStatusClass(b.status)}">${b.status}</span></td>
            <td>${b.cost_range || '—'}</td>
            <td>${b.timeline || '—'}</td>
            <td style="max-width: 200px; overflow: hidden; text-overflow: ellipsis;">${b.notes || '—'}</td>
            <td>
                <button class="action-btn" onclick="editBuilder(${b.id})">Edit</button>
                <button class="action-btn delete" onclick="deleteBuilder(${b.id})">Delete</button>
            </td>
        </tr>
    `).join('');
}

function getStatusClass(status) {
    return status.toLowerCase().replace(/\s+/g, '-');
}

// =============================================================================
// Task Functions
// =============================================================================

async function toggleTask(taskId, completed, existingTime = 0) {
    if (completed) {
        // Ask for time spent when completing a task
        openTimeEntryModal(taskId, existingTime);
    } else {
        // Just uncheck the task
        try {
            await fetch(`/projects/cocoon/api/tasks/${taskId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ completed: false })
            });
            await refreshData();
            showToast('Task unchecked', 'success');
        } catch (error) {
            console.error('Error updating task:', error);
            showToast('Error updating task', 'error');
        }
    }
}

function openTimeEntryModal(taskId, existingMinutes = 0) {
    const hours = Math.floor(existingMinutes / 60);
    const mins = existingMinutes % 60;
    
    document.getElementById('time-task-id').value = taskId;
    document.getElementById('time-hours').value = hours || '';
    document.getElementById('time-minutes').value = mins || '';
    document.getElementById('time-entry-modal').classList.remove('hidden');
    document.getElementById('time-minutes').focus();
}

function closeTimeModal() {
    document.getElementById('time-entry-modal').classList.add('hidden');
}

async function saveTaskTime(event) {
    event.preventDefault();
    
    const taskId = document.getElementById('time-task-id').value;
    const hours = parseInt(document.getElementById('time-hours').value) || 0;
    const minutes = parseInt(document.getElementById('time-minutes').value) || 0;
    const totalMinutes = (hours * 60) + minutes;
    
    try {
        await fetch(`/projects/cocoon/api/tasks/${taskId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                completed: true, 
                time_spent_minutes: totalMinutes,
                assistant_id: currentAssistant?.id || null,
                assistant_name: currentAssistant?.name || null
            })
        });
        closeTimeModal();
        await refreshData();
        loadActivityFeed();  // Refresh activity after task completion
        showToast(`Task completed! (${formatTime(totalMinutes)})`, 'success');
        
        // Get brain guidance for next step
        await getBrainGuidance('task_completed', { time_spent: totalMinutes });
    } catch (error) {
        console.error('Error saving task time:', error);
        showToast('Error saving task', 'error');
    }
}

async function updateTaskTimeOnly(taskId, minutes) {
    try {
        await fetch(`/projects/cocoon/api/tasks/${taskId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ time_spent_minutes: minutes })
        });
        await refreshData();
        showToast('Time updated!', 'success');
    } catch (error) {
        console.error('Error updating time:', error);
        showToast('Error updating time', 'error');
    }
}

function formatTime(minutes) {
    if (!minutes) return '0m';
    const h = Math.floor(minutes / 60);
    const m = minutes % 60;
    if (h > 0 && m > 0) return `${h}h ${m}m`;
    if (h > 0) return `${h}h`;
    return `${m}m`;
}

// =============================================================================
// Builder Functions
// =============================================================================

function openAddBuilder() {
    document.getElementById('modal-title').textContent = 'Add Builder';
    document.getElementById('builder-form').reset();
    document.getElementById('builder-id').value = '';
    document.querySelector('[name="location"]').value = currentLocation;
    document.querySelector('[name="type"]').value = currentLocation === 'Miami' ? 'Local fabricator' : 'Sourcing agent';
    document.getElementById('builder-modal').classList.remove('hidden');
}

async function editBuilder(id) {
    const builder = builders.find(b => b.id === id);
    if (!builder) return;
    
    document.getElementById('modal-title').textContent = 'Edit Builder';
    document.getElementById('builder-id').value = id;
    
    const form = document.getElementById('builder-form');
    form.querySelector('[name="name"]').value = builder.name;
    form.querySelector('[name="location"]').value = builder.location;
    form.querySelector('[name="type"]').value = builder.type;
    form.querySelector('[name="status"]').value = builder.status;
    form.querySelector('[name="contact"]').value = builder.contact || '';
    form.querySelector('[name="cost_range"]').value = builder.cost_range || '';
    form.querySelector('[name="timeline"]').value = builder.timeline || '';
    form.querySelector('[name="materials"]').value = builder.materials || '';
    form.querySelector('[name="notes"]').value = builder.notes || '';
    
    document.getElementById('builder-modal').classList.remove('hidden');
}

async function saveBuilder(event) {
    event.preventDefault();
    const form = event.target;
    const id = document.getElementById('builder-id').value;
    
    const data = {
        name: form.querySelector('[name="name"]').value,
        location: form.querySelector('[name="location"]').value,
        type: form.querySelector('[name="type"]').value,
        status: form.querySelector('[name="status"]').value,
        contact: form.querySelector('[name="contact"]').value || null,
        cost_range: form.querySelector('[name="cost_range"]').value || null,
        timeline: form.querySelector('[name="timeline"]').value || null,
        materials: form.querySelector('[name="materials"]').value || null,
        notes: form.querySelector('[name="notes"]').value || null,
        assistant_id: currentAssistant?.id || null,
        assistant_name: currentAssistant?.name || null
    };
    
    try {
        if (id) {
            await fetch(`/projects/cocoon/api/builders/${id}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            showToast('Builder updated!', 'success');
        } else {
            await fetch('/projects/cocoon/api/builders', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            showToast('Builder added!', 'success');
            
            // Get brain guidance
            await getBrainGuidance('builder_added', { location: data.location, name: data.name });
        }
        closeModal();
        await refreshData();
        loadActivityFeed();
    } catch (error) {
        console.error('Error saving builder:', error);
        showToast('Error saving builder', 'error');
    }
}

async function deleteBuilder(id) {
    if (!confirm('Delete this builder?')) return;
    
    try {
        await fetch(`/api/builders/${id}`, { method: 'DELETE' });
        showToast('Builder deleted', 'success');
        await refreshData();
    } catch (error) {
        console.error('Error deleting builder:', error);
        showToast('Error deleting builder', 'error');
    }
}

function closeModal() {
    document.getElementById('builder-modal').classList.add('hidden');
}

// =============================================================================
// Tracker Tabs
// =============================================================================

function switchTrackerTab(location) {
    currentLocation = location;
    
    // Update tab styles
    document.querySelectorAll('.tracker-tab').forEach(tab => {
        tab.classList.toggle('active', tab.dataset.location === location);
    });
    
    // Re-render builders
    renderBuilders(builders, location);
}

// =============================================================================
// Outreach Messages
// =============================================================================

function copyMessage(type) {
    currentMessageType = type;
    const message = MESSAGES[type];
    
    // Update button styles
    document.querySelectorAll('.outreach-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    event.target.closest('.outreach-btn').classList.add('active');
    
    // Show preview
    document.getElementById('preview-title').textContent = message.title;
    document.getElementById('preview-content').textContent = message.content;
    document.getElementById('message-preview').classList.remove('hidden');
}

function copyToClipboard() {
    const content = MESSAGES[currentMessageType].content;
    navigator.clipboard.writeText(content).then(() => {
        showToast('Message copied to clipboard!', 'success');
    }).catch(err => {
        console.error('Error copying:', err);
        showToast('Error copying message', 'error');
    });
}

// =============================================================================
// Time Tracking
// =============================================================================

async function toggleClock() {
    try {
        if (clockedIn) {
            await fetch('/projects/cocoon/api/time/clock-out', { method: 'POST' });
            showToast('Clocked out!', 'success');
        } else {
            await fetch('/projects/cocoon/api/time/clock-in', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({})
            });
            showToast('Clocked in!', 'success');
        }
        await refreshData();
    } catch (error) {
        console.error('Error toggling clock:', error);
        showToast('Error with clock', 'error');
    }
}

function updateClockButton() {
    const btn = document.getElementById('clock-btn');
    const text = document.getElementById('clock-text');
    
    if (clockedIn) {
        btn.classList.add('active');
        text.textContent = 'Clock Out';
    } else {
        btn.classList.remove('active');
        text.textContent = 'Clock In';
        document.getElementById('elapsed-time').textContent = '';
    }
}

function updateElapsedTime(startTime) {
    const start = new Date(startTime);
    const now = new Date();
    const diff = Math.floor((now - start) / 1000 / 60);
    
    const hours = Math.floor(diff / 60);
    const minutes = diff % 60;
    
    document.getElementById('elapsed-time').textContent = 
        hours > 0 ? `${hours}h ${minutes}m` : `${minutes}m`;
}

// =============================================================================
// Weekly Report
// =============================================================================

async function submitReport(event) {
    event.preventDefault();
    const form = event.target;
    
    const data = {
        week: 1, // TODO: Make dynamic
        moved_forward: form.querySelector('[name="moved_forward"]').value,
        blocked: form.querySelector('[name="blocked"]').value || null,
        needs_decision: form.querySelector('[name="needs_decision"]').value || null,
        recommendation: form.querySelector('[name="recommendation"]').value
    };
    
    try {
        await fetch('/projects/cocoon/api/reports', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        showToast('Report submitted!', 'success');
        form.reset();
    } catch (error) {
        console.error('Error submitting report:', error);
        showToast('Error submitting report', 'error');
    }
}

// =============================================================================
// Toast Notifications
// =============================================================================

function showToast(message, type = 'success') {
    const toast = document.getElementById('toast');
    toast.textContent = message;
    toast.className = `toast ${type}`;
    
    setTimeout(() => {
        toast.classList.add('hidden');
    }, 3000);
}

// =============================================================================
// Data Refresh
// =============================================================================

async function refreshData() {
    const status = await fetchStatus();
    if (!status) return;
    
    // Update current day display
    const currentDay = parseInt(status.settings.current_day) || 1;
    const currentWeek = parseInt(status.settings.current_week) || 1;
    document.getElementById('current-day').textContent = `Week ${currentWeek}, Day ${currentDay}`;
    
    // Render everything
    builders = [...status.builders.miami, ...status.builders.china];
    tasks = status.tasks.items;
    
    renderTodayTasks(tasks, currentDay);
    renderMetrics(status);
    renderBuilders(builders, currentLocation);
}

// =============================================================================
// Initialize
// =============================================================================

document.addEventListener('DOMContentLoaded', () => {
    // Check for assistant registration first
    checkAssistant();
    
    refreshData();
    loadActivityFeed();
    loadActiveAssistants();
    loadBrainStatus();
    
    // Refresh every 30 seconds
    setInterval(refreshData, 30000);
    
    // Refresh activity feed every minute
    setInterval(() => {
        loadActivityFeed();
        loadActiveAssistants();
    }, 60000);
    
    // Update elapsed time every minute if clocked in
    setInterval(() => {
        if (clockedIn) {
            fetchStatus().then(status => {
                if (status && status.time.currently_clocked_in && status.time.active_session_start) {
                    updateElapsedTime(status.time.active_session_start);
                }
            });
        }
    }, 60000);
    
    // Close modal on escape
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            closeModal();
            document.getElementById('assistant-modal')?.classList.add('hidden');
        }
    });
    
    // Close modal on outside click
    document.getElementById('builder-modal').addEventListener('click', (e) => {
        if (e.target.classList.contains('modal')) {
            closeModal();
        }
    });
});

