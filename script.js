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
        this.settingsManager = new SettingsManager(this);
        this.resizeManager = new ResizeManager();
        this.init();
    }

    init() {
        this.bindEvents();
        this.loadInitialData();
        this.settingsManager.init();
        this.resizeManager.init();
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

        // Tab switching functionality
        const tabButtons = document.querySelectorAll('.tab-button');
        tabButtons.forEach(button => {
            button.addEventListener('click', (e) => {
                const targetTab = e.target.getAttribute('data-tab');
                this.switchTab(targetTab);
            });
        });
    }

    switchTab(tabName) {
        // Remove active class from all tab buttons and panels
        document.querySelectorAll('.tab-button').forEach(btn => btn.classList.remove('active'));
        document.querySelectorAll('.tab-panel').forEach(panel => panel.classList.remove('active'));
        
        // Add active class to clicked tab button and corresponding panel
        const targetButton = document.querySelector(`[data-tab="${tabName}"]`);
        const targetPanel = document.getElementById(`${tabName}-tab`);
        
        if (targetButton) targetButton.classList.add('active');
        if (targetPanel) targetPanel.classList.add('active');
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
        
        // Add timestamp if enabled
        if (this.settingsManager.shouldShowTimestamps() && !isLoading) {
            const timestamp = new Date().toLocaleTimeString();
            messageHTML += `<div class="message-timestamp">${timestamp}</div>`;
        }
        
        // Add sources if available
        if (sources && sources.length > 0) {
            messageHTML += '<div class="message-sources">';
            messageHTML += '<h4>Sources:</h4>';
            sources.forEach(source => {
                // Handle both string and object sources
                if (typeof source === 'string') {
                    messageHTML += `<div class="source-item">${source}</div>`;
                } else if (source.link) {
                    messageHTML += `<div class="source-item"><a href="${source.link}" class="source-link" target="_blank">${source.text}</a></div>`;
                } else {
                    messageHTML += `<div class="source-item">${source.text || source}</div>`;
                }
            });
            messageHTML += '</div>';
        }

        messageDiv.innerHTML = messageHTML;
        messagesContainer.appendChild(messageDiv);
        
        // Auto-scroll if enabled
        if (this.settingsManager.shouldAutoScroll()) {
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        }
        
        return messageDiv;
    }

    async loadInitialData() {
        await Promise.all([
            this.loadCourseAnalytics(),
            this.loadSessionLogs(),
            this.loadSampleQuestions()
        ]);
        
        // Start polling for log updates every 2 seconds
        this.startLogPolling();
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
                
                // Auto-scroll to bottom if logs tab is active
                const logsTab = document.getElementById('logs-tab');
                if (logsTab && logsTab.classList.contains('active')) {
                    const logsList = logsContainer.querySelector('.logs-list');
                    if (logsList) {
                        logsList.scrollTop = logsList.scrollHeight;
                    }
                }
            }
        } catch (error) {
            console.error('Error loading session logs:', error);
            const logsContainer = document.getElementById('logsContainer');
            if (logsContainer) {
                logsContainer.innerHTML = 'Error loading session logs';
            }
        }
    }

    startLogPolling() {
        // Poll for log updates every 2 seconds
        this.logPollingInterval = setInterval(() => {
            this.loadSessionLogs();
        }, 2000);
    }

    stopLogPolling() {
        if (this.logPollingInterval) {
            clearInterval(this.logPollingInterval);
            this.logPollingInterval = null;
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

    async loadSampleQuestions() {
        try {
            const response = await fetch('/api/sample-questions');
            const data = await response.json();
            
            const questionsContainer = document.getElementById('sampleQuestions');
            if (questionsContainer) {
                let questionsHTML = '<h4>Sample Questions</h4>';
                
                if (data && data.length > 0) {
                    questionsHTML += '<div class="sample-questions-grid">';
                    data.forEach(question => {
                        questionsHTML += `<button class="sample-question" onclick="chatbot.fillQuestion('${question.question.replace(/'/g, "\\'")}')">`;
                        questionsHTML += `<span class="category">${question.category}</span>`;
                        questionsHTML += `${question.question}`;
                        questionsHTML += `</button>`;
                    });
                    questionsHTML += '</div>';
                } else {
                    questionsHTML += 'No sample questions available';
                }
                
                questionsContainer.innerHTML = questionsHTML;
            }
        } catch (error) {
            console.error('Error loading sample questions:', error);
            const questionsContainer = document.getElementById('sampleQuestions');
            if (questionsContainer) {
                questionsContainer.innerHTML = '<h4>Sample Questions</h4>Error loading sample questions';
            }
        }
    }

    fillQuestion(question) {
        const messageInput = document.getElementById('messageInput');
        if (messageInput) {
            messageInput.value = question;
            messageInput.focus();
        }
    }
}

// Resize Manager for Sidebar
class ResizeManager {
    constructor() {
        this.isResizing = false;
        this.startX = 0;
        this.startWidth = 0;
        this.sidebar = null;
        this.resizeHandle = null;
        this.minWidth = 280;
        this.maxWidth = 600;
    }

    init() {
        this.sidebar = document.getElementById('sidebar');
        this.resizeHandle = document.getElementById('resizeHandle');
        
        if (!this.sidebar || !this.resizeHandle) {
            console.warn('Sidebar or resize handle not found');
            return;
        }

        // Load saved width from localStorage
        const savedWidth = localStorage.getItem('sidebarWidth');
        if (savedWidth) {
            const width = parseInt(savedWidth, 10);
            if (width >= this.minWidth && width <= this.maxWidth) {
                this.sidebar.style.width = width + 'px';
            }
        }

        this.bindEvents();
    }

    bindEvents() {
        // Mouse events
        this.resizeHandle.addEventListener('mousedown', (e) => this.startResize(e));
        document.addEventListener('mousemove', (e) => this.handleResize(e));
        document.addEventListener('mouseup', () => this.stopResize());

        // Touch events for mobile
        this.resizeHandle.addEventListener('touchstart', (e) => this.startResize(e.touches[0]));
        document.addEventListener('touchmove', (e) => this.handleResize(e.touches[0]));
        document.addEventListener('touchend', () => this.stopResize());

        // Prevent text selection during resize
        this.resizeHandle.addEventListener('selectstart', (e) => e.preventDefault());
    }

    startResize(event) {
        this.isResizing = true;
        this.startX = event.clientX;
        this.startWidth = parseInt(document.defaultView.getComputedStyle(this.sidebar).width, 10);
        
        // Add visual feedback
        document.body.style.cursor = 'col-resize';
        document.body.style.userSelect = 'none';
        document.body.classList.add('resizing');
        this.sidebar.style.transition = 'none';
        
        // Add a class to indicate resizing state
        this.sidebar.classList.add('resizing');
        
        event.preventDefault();
    }

    handleResize(event) {
        if (!this.isResizing) return;

        const currentX = event.clientX;
        const dx = this.startX - currentX; // Note: reversed because handle is on left
        const newWidth = this.startWidth + dx;

        // Constrain within min/max bounds
        const constrainedWidth = Math.max(this.minWidth, Math.min(this.maxWidth, newWidth));
        
        this.sidebar.style.width = constrainedWidth + 'px';
        
        event.preventDefault();
    }

    stopResize() {
        if (!this.isResizing) return;

        this.isResizing = false;
        
        // Remove visual feedback
        document.body.style.cursor = '';
        document.body.style.userSelect = '';
        document.body.classList.remove('resizing');
        this.sidebar.style.transition = '';
        this.sidebar.classList.remove('resizing');

        // Save the current width to localStorage
        const currentWidth = parseInt(this.sidebar.style.width, 10);
        localStorage.setItem('sidebarWidth', currentWidth.toString());
    }

    // Method to programmatically set sidebar width
    setSidebarWidth(width) {
        const constrainedWidth = Math.max(this.minWidth, Math.min(this.maxWidth, width));
        this.sidebar.style.width = constrainedWidth + 'px';
        localStorage.setItem('sidebarWidth', constrainedWidth.toString());
    }

    // Method to reset to default width
    resetToDefault() {
        this.setSidebarWidth(350); // Default width
    }
}

// Settings Manager
class SettingsManager {
    constructor(chatbot) {
        this.chatbot = chatbot;
        this.settings = {
            autoScroll: true,
            showTimestamps: false,
            typingIndicators: true,
            reducedMotion: false,
            highContrast: false,
            saveHistory: true,
            theme: 'dark'
        };
        this.loadSettings();
    }

    init() {
        this.bindSettingsEvents();
        this.updateThemeButtons();
        this.applySettings();
    }

    bindSettingsEvents() {
        // Theme selection buttons
        const themeButtons = document.querySelectorAll('.theme-option');
        themeButtons.forEach(button => {
            button.addEventListener('click', (e) => {
                const theme = e.currentTarget.getAttribute('data-theme');
                this.setTheme(theme);
            });
        });

        // Toggle switches
        const toggles = [
            'autoScroll', 'showTimestamps', 'typingIndicators', 
            'reducedMotion', 'highContrast', 'saveHistory'
        ];

        toggles.forEach(setting => {
            const toggle = document.getElementById(setting);
            if (toggle) {
                toggle.checked = this.settings[setting];
                toggle.addEventListener('change', (e) => {
                    this.updateSetting(setting, e.target.checked);
                });
            }
        });

        // Clear all data button
        const clearDataButton = document.getElementById('clearAllData');
        if (clearDataButton) {
            clearDataButton.addEventListener('click', () => {
                this.clearAllData();
            });
        }
    }

    setTheme(theme) {
        this.settings.theme = theme;
        
        if (theme === 'auto') {
            // Use system preference
            const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
            const systemTheme = mediaQuery.matches ? 'dark' : 'light';
            this.chatbot.themeManager.setTheme(systemTheme);
            
            // Listen for system changes
            mediaQuery.addEventListener('change', (e) => {
                if (this.settings.theme === 'auto') {
                    this.chatbot.themeManager.setTheme(e.matches ? 'dark' : 'light');
                }
            });
        } else {
            this.chatbot.themeManager.setTheme(theme);
        }
        
        this.updateThemeButtons();
        this.saveSettings();
    }

    updateThemeButtons() {
        const themeButtons = document.querySelectorAll('.theme-option');
        themeButtons.forEach(button => {
            const buttonTheme = button.getAttribute('data-theme');
            button.classList.toggle('active', buttonTheme === this.settings.theme);
        });
    }

    updateSetting(key, value) {
        this.settings[key] = value;
        this.applySettings();
        this.saveSettings();
    }

    applySettings() {
        // Apply reduced motion
        if (this.settings.reducedMotion) {
            document.documentElement.style.setProperty('--transition-duration', '0s');
            document.documentElement.classList.add('reduced-motion');
        } else {
            document.documentElement.style.removeProperty('--transition-duration');
            document.documentElement.classList.remove('reduced-motion');
        }

        // Apply high contrast
        if (this.settings.highContrast) {
            document.documentElement.classList.add('high-contrast');
        } else {
            document.documentElement.classList.remove('high-contrast');
        }

        // Update message timestamps visibility
        const messages = document.querySelectorAll('.message');
        messages.forEach(message => {
            const timestamp = message.querySelector('.message-timestamp');
            if (timestamp) {
                timestamp.style.display = this.settings.showTimestamps ? 'block' : 'none';
            }
        });
    }

    clearAllData() {
        if (confirm('Are you sure you want to clear all data? This will remove all conversations, logs, and settings. This action cannot be undone.')) {
            // Clear localStorage
            localStorage.clear();
            
            // Clear messages
            const messagesContainer = document.getElementById('messages');
            if (messagesContainer) {
                messagesContainer.innerHTML = `
                    <div class="message assistant-message">
                        <div class="message-content">
                            Hello! I'm your RAG chatbot assistant. Ask me anything about the available courses and content.
                        </div>
                    </div>
                `;
            }

            // Clear logs via API
            this.chatbot.clearLogs();

            // Reset settings to defaults
            this.settings = {
                autoScroll: true,
                showTimestamps: false,
                typingIndicators: true,
                reducedMotion: false,
                highContrast: false,
                saveHistory: true,
                theme: 'dark'
            };

            // Reset UI
            this.init();
            this.chatbot.themeManager.setTheme('dark');

            alert('All data has been cleared successfully.');
        }
    }

    loadSettings() {
        const saved = localStorage.getItem('chatbotSettings');
        if (saved) {
            try {
                const parsed = JSON.parse(saved);
                this.settings = { ...this.settings, ...parsed };
            } catch (e) {
                console.warn('Failed to parse saved settings:', e);
            }
        }
    }

    saveSettings() {
        localStorage.setItem('chatbotSettings', JSON.stringify(this.settings));
    }

    // Getter methods for other parts of the app
    shouldAutoScroll() {
        return this.settings.autoScroll;
    }

    shouldShowTimestamps() {
        return this.settings.showTimestamps;
    }

    shouldShowTypingIndicators() {
        return this.settings.typingIndicators;
    }

    shouldSaveHistory() {
        return this.settings.saveHistory;
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