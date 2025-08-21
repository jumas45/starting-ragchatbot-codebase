// API base URL - use relative path to work from any host
const API_URL = '/api';

// Global state
let currentSessionId = null;

// DOM elements
let chatMessages, chatInput, sendButton, totalCourses, courseTitles, newChatButton, logMessages, clearLogsButton;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    // Get DOM elements after page loads
    chatMessages = document.getElementById('chatMessages');
    chatInput = document.getElementById('chatInput');
    sendButton = document.getElementById('sendButton');
    totalCourses = document.getElementById('totalCourses');
    courseTitles = document.getElementById('courseTitles');
    newChatButton = document.getElementById('newChatButton');
    logMessages = document.getElementById('logMessages');
    clearLogsButton = document.getElementById('clearLogsButton');
    
    setupEventListeners();
    createNewSession();
    loadCourseStats();
    loadLogs();
});

// Event Listeners
function setupEventListeners() {
    // Chat functionality
    sendButton.addEventListener('click', sendMessage);
    chatInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendMessage();
    });
    
    // New chat button
    newChatButton.addEventListener('click', createNewSession);
    
    // Tab switching
    document.querySelectorAll('.tab-button').forEach(button => {
        button.addEventListener('click', (e) => {
            const tabName = e.target.getAttribute('data-tab');
            switchTab(tabName);
        });
    });
    
    // Clear logs button
    if (clearLogsButton) {
        clearLogsButton.addEventListener('click', clearLogs);
    }
    
    // Suggested questions
    document.querySelectorAll('.suggested-item').forEach(button => {
        button.addEventListener('click', (e) => {
            const question = e.target.getAttribute('data-question');
            chatInput.value = question;
            sendMessage();
        });
    });
}


// Chat Functions
async function sendMessage() {
    const query = chatInput.value.trim();
    if (!query) return;

    // Disable input
    chatInput.value = '';
    chatInput.disabled = true;
    sendButton.disabled = true;

    // Add user message
    addMessage(query, 'user');

    // Add loading message - create a unique container for it
    const loadingMessage = createLoadingMessage();
    chatMessages.appendChild(loadingMessage);
    chatMessages.scrollTop = chatMessages.scrollHeight;

    try {
        const response = await fetch(`${API_URL}/query`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                query: query,
                session_id: currentSessionId
            })
        });

        if (!response.ok) throw new Error('Query failed');

        const data = await response.json();
        
        // Update session ID if new
        if (!currentSessionId) {
            currentSessionId = data.session_id;
        }

        // Replace loading message with response
        loadingMessage.remove();
        addMessage(data.answer, 'assistant', data.sources);

    } catch (error) {
        // Replace loading message with error
        loadingMessage.remove();
        addMessage(`Error: ${error.message}`, 'assistant');
    } finally {
        chatInput.disabled = false;
        sendButton.disabled = false;
        chatInput.focus();
    }
}

function createLoadingMessage() {
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message assistant';
    messageDiv.innerHTML = `
        <div class="message-content">
            <div class="loading">
                <span></span>
                <span></span>
                <span></span>
            </div>
        </div>
    `;
    return messageDiv;
}

function addMessage(content, type, sources = null, isWelcome = false) {
    const messageId = Date.now();
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${type}${isWelcome ? ' welcome-message' : ''}`;
    messageDiv.id = `message-${messageId}`;
    
    // Convert markdown to HTML for assistant messages
    const displayContent = type === 'assistant' ? marked.parse(content) : escapeHtml(content);
    
    let html = `<div class="message-content">${displayContent}</div>`;
    
    if (sources && sources.length > 0) {
        // Process sources to create clickable links
        const sourceItems = sources.map(source => {
            if (source.link) {
                return `<a href="${source.link}" target="_blank" rel="noopener noreferrer">${source.text}</a>`;
            } else {
                return source.text;
            }
        });
        
        html += `
            <details class="sources-collapsible">
                <summary class="sources-header">Sources</summary>
                <div class="sources-content">${sourceItems.join(', ')}</div>
            </details>
        `;
    }
    
    messageDiv.innerHTML = html;
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
    
    return messageId;
}

// Helper function to escape HTML for user messages
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Removed removeMessage function - no longer needed since we handle loading differently

async function createNewSession() {
    // Reset session state
    currentSessionId = null;
    
    // Clear chat messages
    chatMessages.innerHTML = '';
    
    // Reset input state
    chatInput.value = '';
    chatInput.disabled = false;
    sendButton.disabled = false;
    
    // Focus on input for immediate use
    chatInput.focus();
    
    // Add welcome message
    addMessage('Welcome to the Course Materials Assistant! I can help you with questions about courses, lessons and specific content. What would you like to know?', 'assistant', null, true);
}

// Load course statistics
async function loadCourseStats() {
    try {
        console.log('Loading course stats...');
        const response = await fetch(`${API_URL}/courses`);
        if (!response.ok) throw new Error('Failed to load course stats');
        
        const data = await response.json();
        console.log('Course data received:', data);
        
        // Update stats in UI
        if (totalCourses) {
            totalCourses.textContent = data.total_courses;
        }
        
        // Update course titles
        if (courseTitles) {
            if (data.course_titles && data.course_titles.length > 0) {
                courseTitles.innerHTML = data.course_titles
                    .map(title => `<div class="course-title-item">${title}</div>`)
                    .join('');
            } else {
                courseTitles.innerHTML = '<span class="no-courses">No courses available</span>';
            }
        }
        
    } catch (error) {
        console.error('Error loading course stats:', error);
        // Set default values on error
        if (totalCourses) {
            totalCourses.textContent = '0';
        }
        if (courseTitles) {
            courseTitles.innerHTML = '<span class="error">Failed to load courses</span>';
        }
    }
}

// Tab Functions
function switchTab(tabName) {
    // Update tab buttons
    document.querySelectorAll('.tab-button').forEach(button => {
        button.classList.remove('active');
    });
    document.querySelector(`[data-tab="${tabName}"]`).classList.add('active');
    
    // Update tab content
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.remove('active');
    });
    document.getElementById(`${tabName}Tab`).classList.add('active');
    
    // Load logs if switching to logs tab
    if (tabName === 'logs') {
        loadLogs();
    }
}

// Log Functions
async function loadLogs() {
    if (!logMessages) return;
    
    try {
        const response = await fetch(`${API_URL}/logs`);
        if (!response.ok) throw new Error('Failed to load logs');
        
        const logs = await response.json();
        
        if (logs.length === 0) {
            logMessages.innerHTML = '<div class="log-entry">No logs available</div>';
        } else {
            logMessages.innerHTML = logs.map(log => {
                const timestamp = new Date(log.timestamp).toLocaleString();
                return `
                    <div class="log-entry">
                        <span class="log-timestamp">${timestamp}</span>
                        <span class="log-level ${log.level}">${log.level}</span>
                        <span class="log-message">${escapeHtml(log.message)}</span>
                    </div>
                `;
            }).join('');
        }
        
        // Auto scroll to bottom
        logMessages.scrollTop = logMessages.scrollHeight;
        
    } catch (error) {
        console.error('Error loading logs:', error);
        if (logMessages) {
            logMessages.innerHTML = '<div class="log-entry error">Failed to load logs</div>';
        }
    }
}

async function clearLogs() {
    try {
        const response = await fetch(`${API_URL}/logs/clear`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        });
        
        if (!response.ok) throw new Error('Failed to clear logs');
        
        // Reload logs to show empty state
        loadLogs();
        
    } catch (error) {
        console.error('Error clearing logs:', error);
    }
}

// Auto-refresh logs every 2 seconds when on logs tab
setInterval(() => {
    const logsTab = document.getElementById('logsTab');
    if (logsTab && logsTab.classList.contains('active')) {
        loadLogs();
    }
}, 2000);