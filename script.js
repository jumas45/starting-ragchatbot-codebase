// Theme Management
class ThemeManager {
    constructor() {
        this.init();
    }

    init() {
        // Get saved theme from localStorage or default to 'dark'
        const savedTheme = localStorage.getItem('theme') || 'dark';
        this.setTheme(savedTheme);
        
        // Bind theme toggle event
        const themeToggle = document.getElementById('themeToggle');
        if (themeToggle) {
            themeToggle.addEventListener('click', () => this.toggleTheme());
            themeToggle.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    this.toggleTheme();
                }
            });
        }
    }

    setTheme(theme) {
        document.documentElement.setAttribute('data-theme', theme);
        localStorage.setItem('theme', theme);
        
        // Update ARIA label for accessibility
        const themeToggle = document.getElementById('themeToggle');
        if (themeToggle) {
            themeToggle.setAttribute('aria-label', 
                theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme'
            );
        }
    }

    toggleTheme() {
        const currentTheme = document.documentElement.getAttribute('data-theme');
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
        this.setTheme(newTheme);
    }

    getCurrentTheme() {
        return document.documentElement.getAttribute('data-theme');
    }
}

// RAG Chatbot Application
class RAGChatbot {
    constructor() {
        this.sessionId = this.generateSessionId();
        this.themeManager = new ThemeManager();
        this.init();
    }

    init() {
        this.bindEvents();
        this.loadInitialData();
    }

    generateSessionId() {
        return 'session_' + Math.random().toString(36).substr(2, 9) + '_' + Date.now();
    }

    bindEvents() {
        const sendButton = document.getElementById('sendButton');
        const messageInput = document.getElementById('messageInput');
        const clearLogsButton = document.getElementById('clearLogsButton');

        if (sendButton) {
            sendButton.addEventListener('click', () => this.sendMessage());
        }

        if (messageInput) {
            messageInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    this.sendMessage();
                }
            });
        }

        if (clearLogsButton) {
            clearLogsButton.addEventListener('click', () => this.clearLogs());
        }
    }

    async sendMessage() {
        const messageInput = document.getElementById('messageInput');
        const message = messageInput.value.trim();
        
        if (!message) return;

        // Clear input and add user message to UI
        messageInput.value = '';
        this.addMessageToUI(message, 'user');

        try {
            // Show loading state
            const loadingMessage = this.addMessageToUI('Thinking...', 'assistant', true);

            // Send query to backend
            const response = await fetch('/api/query', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    query: message,
                    session_id: this.sessionId
                })
            });

            const data = await response.json();

            // Remove loading message
            if (loadingMessage) {
                loadingMessage.remove();
            }

            // Add assistant response
            this.addMessageToUI(data.answer, 'assistant', false, data.sources);

        } catch (error) {
            console.error('Error sending message:', error);
            // Remove loading message
            const loadingMessage = document.querySelector('.message.loading');
            if (loadingMessage) {
                loadingMessage.remove();
            }
            
            this.addMessageToUI('Sorry, there was an error processing your request.', 'assistant');
        }
    }

    addMessageToUI(content, type, isLoading = false, sources = null) {
        const messagesContainer = document.getElementById('messages');
        const messageDiv = document.createElement('div');
        
        messageDiv.className = `message ${type}-message`;
        if (isLoading) {
            messageDiv.classList.add('loading');
        }

        let messageHTML = `<div class="message-content">${content}</div>`;
        
        // Add sources if available
        if (sources && sources.length > 0) {
            messageHTML += '<div class="message-sources">';
            messageHTML += '<h4>Sources:</h4>';
            sources.forEach(source => {
                if (source.link) {
                    messageHTML += `<div class="source-item"><a href="${source.link}" class="source-link" target="_blank">${source.text}</a></div>`;
                } else {
                    messageHTML += `<div class="source-item">${source.text}</div>`;
                }
            });
            messageHTML += '</div>';
        }

        messageDiv.innerHTML = messageHTML;
        messagesContainer.appendChild(messageDiv);
        
        // Scroll to bottom
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
        
        return messageDiv;
    }

    async loadInitialData() {
        await Promise.all([
            this.loadCourseAnalytics(),
            this.loadSessionLogs()
        ]);
    }

    async loadCourseAnalytics() {
        try {
            const response = await fetch('/api/courses');
            const data = await response.json();
            
            const analyticsContainer = document.getElementById('courseAnalytics');
            if (analyticsContainer) {
                let analyticsHTML = '';
                
                if (data.courses && data.courses.length > 0) {
                    analyticsHTML = '<ul>';
                    data.courses.forEach(course => {
                        analyticsHTML += `<li><strong>${course.title}</strong><br>`;
                        analyticsHTML += `Lessons: ${course.lesson_count || 'N/A'}<br>`;
                        analyticsHTML += `Instructor: ${course.instructor || 'N/A'}</li>`;
                    });
                    analyticsHTML += '</ul>';
                } else {
                    analyticsHTML = 'No course data available';
                }
                
                analyticsContainer.innerHTML = analyticsHTML;
            }
        } catch (error) {
            console.error('Error loading course analytics:', error);
            const analyticsContainer = document.getElementById('courseAnalytics');
            if (analyticsContainer) {
                analyticsContainer.innerHTML = 'Error loading course data';
            }
        }
    }

    async loadSessionLogs() {
        try {
            const response = await fetch('/api/logs');
            const data = await response.json();
            
            const logsContainer = document.getElementById('logsContainer');
            if (logsContainer) {
                let logsHTML = '';
                
                if (data.logs && data.logs.length > 0) {
                    logsHTML = '<div class="logs-list">';
                    data.logs.forEach(log => {
                        logsHTML += `<div class="log-entry">`;
                        logsHTML += `<strong>${log.timestamp || 'Unknown time'}:</strong> `;
                        logsHTML += `${log.message || 'No message'}`;
                        if (log.tokens) {
                            logsHTML += ` (${log.tokens} tokens)`;
                        }
                        logsHTML += `</div>`;
                    });
                    logsHTML += '</div>';
                } else {
                    logsHTML = 'No session logs available';
                }
                
                logsContainer.innerHTML = logsHTML;
            }
        } catch (error) {
            console.error('Error loading session logs:', error);
            const logsContainer = document.getElementById('logsContainer');
            if (logsContainer) {
                logsContainer.innerHTML = 'Error loading session logs';
            }
        }
    }

    async clearLogs() {
        try {
            await fetch('/api/logs/clear', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            });
            
            // Reload logs after clearing
            await this.loadSessionLogs();
        } catch (error) {
            console.error('Error clearing logs:', error);
        }
    }
}

// System Theme Detection and Auto-switching
class SystemThemeDetector {
    constructor(themeManager) {
        this.themeManager = themeManager;
        this.init();
    }

    init() {
        // Check if user prefers reduced motion
        const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
        if (prefersReducedMotion.matches) {
            document.documentElement.style.setProperty('--transition-duration', '0s');
        }

        // Listen for system theme changes
        const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
        
        // Only auto-switch if no user preference is saved
        if (!localStorage.getItem('theme')) {
            this.themeManager.setTheme(mediaQuery.matches ? 'dark' : 'light');
        }

        // Listen for changes (user might change system theme)
        mediaQuery.addEventListener('change', (e) => {
            // Only auto-switch if no user preference is saved
            if (!localStorage.getItem('theme')) {
                this.themeManager.setTheme(e.matches ? 'dark' : 'light');
            }
        });
    }
}

// Keyboard Shortcuts
class KeyboardShortcuts {
    constructor(chatbot) {
        this.chatbot = chatbot;
        this.init();
    }

    init() {
        document.addEventListener('keydown', (e) => {
            // Ctrl/Cmd + K to focus message input
            if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
                e.preventDefault();
                const messageInput = document.getElementById('messageInput');
                if (messageInput) {
                    messageInput.focus();
                }
            }

            // Ctrl/Cmd + Shift + T to toggle theme
            if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === 'T') {
                e.preventDefault();
                this.chatbot.themeManager.toggleTheme();
            }

            // Escape to clear message input
            if (e.key === 'Escape') {
                const messageInput = document.getElementById('messageInput');
                if (messageInput && document.activeElement === messageInput) {
                    messageInput.value = '';
                    messageInput.blur();
                }
            }
        });
    }
}

// Initialize the application when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    const chatbot = new RAGChatbot();
    const systemThemeDetector = new SystemThemeDetector(chatbot.themeManager);
    const keyboardShortcuts = new KeyboardShortcuts(chatbot);
    
    // Make chatbot available globally for debugging
    window.chatbot = chatbot;
    
    console.log('RAG Chatbot initialized with theme support');
    console.log('Keyboard shortcuts:');
    console.log('  Ctrl/Cmd + K: Focus message input');
    console.log('  Ctrl/Cmd + Shift + T: Toggle theme');
    console.log('  Escape: Clear message input (when focused)');
});