// MaybeBot Dashboard JavaScript
class Dashboard {
    constructor() {
        this.currentGuild = null;
        this.user = null;
        this.guilds = [];
        this.channels = [];
        this.currentLanguage = 'en';
        this.availableLanguages = [];
        this.strings = {};
        this.init();
    }

    async init() {
        try {
            // Get access token from cookie
            const token = this.getCookie('access_token');
            if (!token) {
                window.location.href = '/';
                return;
            }

            // Load available languages first
            await this.loadAvailableLanguages();
            
            // Load user's language preference
            await this.loadUserLanguage();
            
            // Load language strings
            await this.loadLanguageStrings();
            
            // Initialize language selector
            this.initLanguageSelector();
            
            // Load user data
            await this.loadUser();
            await this.loadGuilds();
            
            // Update UI with translations
            this.updateUILanguage();
            
            // Hide loading overlay
            document.getElementById('loadingOverlay').style.display = 'none';
            document.getElementById('dashboardContent').style.display = 'block';
            
        } catch (error) {
            console.error('Initialization error:', error);
            this.showError('Failed to load dashboard. Please try logging in again.');
        }
    }

    getCookie(name) {
        const value = `; ${document.cookie}`;
        const parts = value.split(`; ${name}=`);
        if (parts.length === 2) return parts.pop().split(';').shift();
    }

    async apiCall(endpoint, method = 'GET', data = null) {
        const token = this.getCookie('access_token');
        const options = {
            method,
            headers: {
                'Content-Type': 'application/json'
            }
        };

        if (token) {
            options.headers['Authorization'] = `Bearer ${token}`;
        }

        if (data) {
            options.body = JSON.stringify(data);
        }

        const response = await fetch(`/api${endpoint}`, options);
        
        if (!response.ok) {
            if (response.status === 401) {
                // Clear invalid token and redirect to login
                document.cookie = 'access_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
                window.location.href = '/';
                return;
            }
            throw new Error(`API call failed: ${response.statusText}`);
        }

        return await response.json();
    }

    async loadUser() {
        try {
            this.user = await this.apiCall('/user/me');
            
            // Update navbar with user info
            const usernameEl = document.getElementById('username');
            const avatarEl = document.getElementById('userAvatar');
            
            usernameEl.textContent = this.user.username;
            
            if (this.user.avatar) {
                avatarEl.src = `https://cdn.discordapp.com/avatars/${this.user.id}/${this.user.avatar}.png`;
                avatarEl.style.display = 'inline';
            }
            
        } catch (error) {
            console.error('Failed to load user:', error);
            throw error;
        }
    }

    async loadGuilds() {
        try {
            this.guilds = this.user.guilds || [];
            
            const guildSelector = document.getElementById('guildSelector');
            guildSelector.innerHTML = '<option value="">Select a server...</option>';
            
            this.guilds.forEach(guild => {
                const option = document.createElement('option');
                option.value = guild.id;
                option.textContent = guild.name;
                guildSelector.appendChild(option);
            });
            
            if (this.guilds.length === 0) {
                this.showError('No manageable servers found. Make sure the bot is in your server and you have administrator permissions.');
            }
            
        } catch (error) {
            console.error('Failed to load guilds:', error);
            throw error;
        }
    }

    // Language support methods
    async loadAvailableLanguages() {
        try {
            const response = await this.apiCall('/languages');
            this.availableLanguages = response.languages;
        } catch (error) {
            console.error('Failed to load available languages:', error);
            // Fallback to English only
            this.availableLanguages = [{ code: 'en', name: 'English', flag: '🇺🇸' }];
        }
    }

    async loadUserLanguage() {
        try {
            const response = await this.apiCall('/user/language');
            this.currentLanguage = response.language;
        } catch (error) {
            console.error('Failed to load user language:', error);
            this.currentLanguage = 'en';
        }
    }

    async loadLanguageStrings() {
        try {
            const response = await this.apiCall(`/language/${this.currentLanguage}`);
            this.strings = response;
        } catch (error) {
            console.error('Failed to load language strings:', error);
            // Fallback to basic English strings
            this.strings = {
                navigation: { dashboard: 'Dashboard', overview: 'Overview' },
                common: { loading: 'Loading...' }
            };
        }
    }

    initLanguageSelector() {
        const languageMenu = document.getElementById('languageMenu');
        const currentLanguageEl = document.getElementById('currentLanguage');
        
        // Clear existing menu
        languageMenu.innerHTML = '';
        
        // Add available languages
        this.availableLanguages.forEach(lang => {
            const li = document.createElement('li');
            li.innerHTML = `<a class="dropdown-item" href="#" onclick="dashboard.changeLanguage('${lang.code}')">${lang.flag} ${lang.name}</a>`;
            languageMenu.appendChild(li);
        });
        
        // Update current language display
        const currentLang = this.availableLanguages.find(lang => lang.code === this.currentLanguage);
        if (currentLang) {
            currentLanguageEl.textContent = `${currentLang.flag} ${currentLang.name}`;
        }
    }

    async changeLanguage(languageCode) {
        try {
            // Save language preference
            await this.apiCall('/user/language', 'PUT', { language: languageCode });
            
            // Update current language
            this.currentLanguage = languageCode;
            
            // Load new language strings
            await this.loadLanguageStrings();
            
            // Update UI
            this.updateUILanguage();
            this.initLanguageSelector();
            
            // Show success message
            this.showSuccess(this.getString('language.language_changed') || 'Language changed successfully!');
            
        } catch (error) {
            console.error('Failed to change language:', error);
            this.showError(this.getString('language.language_error') || 'Error changing language');
        }
    }

    getString(key) {
        const keys = key.split('.');
        let value = this.strings;
        
        for (const k of keys) {
            if (value && typeof value === 'object') {
                value = value[k];
            } else {
                return key; // Return the key if translation not found
            }
        }
        
        return value || key;
    }

    updateUILanguage() {
        // Update all elements with data-translate attribute
        const translatableElements = document.querySelectorAll('[data-translate]');
        translatableElements.forEach(element => {
            const key = element.getAttribute('data-translate');
            const translation = this.getString(key);
            if (translation && translation !== key) {
                element.textContent = translation;
            }
        });

        // Update navigation links (preserve icons)
        const navigationElements = {
            'overview': document.querySelector('a[href="#overview"]'),
            'xp-settings': document.querySelector('a[href="#xp-settings"]'),
            'moderation': document.querySelector('a[href="#moderation"]'),
            'welcome': document.querySelector('a[href="#welcome"]'),
            'logs': document.querySelector('a[href="#logs"]')
        };

        if (navigationElements.overview) {
            navigationElements.overview.innerHTML = `<i class="fas fa-tachometer-alt me-2"></i>${this.getString('navigation.overview')}`;
        }
        if (navigationElements['xp-settings']) {
            navigationElements['xp-settings'].innerHTML = `<i class="fas fa-trophy me-2"></i>${this.getString('navigation.xp_system')}`;
        }
        if (navigationElements.moderation) {
            navigationElements.moderation.innerHTML = `<i class="fas fa-shield-alt me-2"></i>${this.getString('navigation.moderation')}`;
        }
        if (navigationElements.welcome) {
            navigationElements.welcome.innerHTML = `<i class="fas fa-door-open me-2"></i>${this.getString('navigation.welcome_system')}`;
        }
        if (navigationElements.logs) {
            navigationElements.logs.innerHTML = `<i class="fas fa-file-alt me-2"></i>${this.getString('navigation.server_logs')}`;
        }

        // Update logout link
        const logoutLink = document.querySelector('a[onclick="logout()"]');
        if (logoutLink) {
            logoutLink.textContent = this.getString('navigation.logout');
        }

        // Update other specific sections
        this.updateSectionTitles();
    }

    updateSectionTitles() {
        // Update section titles that might not have data-translate attributes
        const xpTitle = document.querySelector('#xp-settings .card-title');
        if (xpTitle) {
            xpTitle.textContent = this.getString('xp_system.title');
        }
        
        const moderationTitle = document.querySelector('#moderation .card-title');
        if (moderationTitle) {
            moderationTitle.textContent = this.getString('moderation.title');
        }
        
        const welcomeTitle = document.querySelector('#welcome .card-title');
        if (welcomeTitle) {
            welcomeTitle.textContent = this.getString('welcome.title');
        }
        
        const logsTitle = document.querySelector('#logs .card-title');
        if (logsTitle) {
            logsTitle.textContent = this.getString('logs.title');
        }
    }

    async selectGuild() {
        const guildSelector = document.getElementById('guildSelector');
        const guildId = guildSelector.value;
        
        if (!guildId) {
            this.currentGuild = null;
            return;
        }

        this.currentGuild = guildId;
        
        try {
            // Load guild data
            await this.loadGuildStats();
            await this.loadGuildConfig();
            await this.loadGuildChannels();
            await this.loadGuildMembers();
            await this.loadModerationHistory();
            await this.loadWelcomeConfig();
            await this.loadServerLogsConfig();
            
        } catch (error) {
            console.error('Failed to load guild data:', error);
            this.showError('Failed to load server data.');
        }
    }

    async loadGuildStats() {
        if (!this.currentGuild) return;

        try {
            const stats = await this.apiCall(`/guild/${this.currentGuild}/stats`);
            
            // Update overview cards
            document.getElementById('totalMembers').textContent = stats.total_members?.toLocaleString() || '0';
            document.getElementById('totalXP').textContent = stats.total_xp?.toLocaleString() || '0';
            document.getElementById('avgLevel').textContent = stats.average_level || '0';
            document.getElementById('recentActivity').textContent = stats.recent_activity?.toLocaleString() || '0';
            
            // Update top users table
            const topUsersTable = document.getElementById('topUsersTable');
            topUsersTable.innerHTML = '';
            
            if (stats.top_users && stats.top_users.length > 0) {
                stats.top_users.forEach((user, index) => {
                    const row = document.createElement('tr');
                    row.innerHTML = `
                        <td><span class="badge bg-primary">#${index + 1}</span></td>
                        <td>${user.user_id}</td>
                        <td><span class="badge bg-success">Level ${user.level}</span></td>
                        <td>${user.xp?.toLocaleString() || '0'} XP</td>
                    `;
                    topUsersTable.appendChild(row);
                });
            } else {
                topUsersTable.innerHTML = '<tr><td colspan="4" class="text-center text-muted">No data available</td></tr>';
            }
            
        } catch (error) {
            console.error('Failed to load guild stats:', error);
        }
    }

    async loadGuildConfig() {
        if (!this.currentGuild) return;

        try {
            const config = await this.apiCall(`/guild/${this.currentGuild}/config`);
            
            // Update XP settings form with enhanced fields
            document.getElementById('xpEnabled').checked = config.xp_enabled !== false;
            document.getElementById('xpMultiplier').value = config.xp_multiplier || 1.0;
            document.getElementById('levelUpMessage').checked = config.level_up_message !== false;
            
            // Set XP channel
            if (config.xp_channel) {
                document.getElementById('xpChannel').value = config.xp_channel;
            } else {
                document.getElementById('xpChannel').value = '';
            }
            
            // Set level up channel
            if (config.level_up_channel) {
                document.getElementById('levelUpChannel').value = config.level_up_channel;
            } else {
                document.getElementById('levelUpChannel').value = '';
            }
            
        } catch (error) {
            console.error('Failed to load guild config:', error);
        }
    }

    async loadGuildChannels() {
        if (!this.currentGuild) return;

        try {
            console.log('Loading channels for guild:', this.currentGuild);
            this.channels = await this.apiCall(`/guild/${this.currentGuild}/channels`);
            console.log('Loaded channels:', this.channels);
            
            // Update channel selectors for XP, welcome, server logs, and moderation
            const channelSelectors = ['xpChannel', 'levelUpChannel', 'welcomeChannel', 'goodbyeChannel', 'serverLogsChannel', 'moderationChannel'];
            
            channelSelectors.forEach(selectorId => {
                const selector = document.getElementById(selectorId);
                if (!selector) return;
                
                const currentValue = selector.value;
                
                // Clear existing options except the first one
                while (selector.children.length > 1) {
                    selector.removeChild(selector.lastChild);
                }
                
                // Add channel options
                if (this.channels && this.channels.length > 0) {
                    this.channels.forEach(channel => {
                        const option = document.createElement('option');
                        option.value = channel.id;
                        option.textContent = `#${channel.name}`;
                        selector.appendChild(option);
                    });
                } else {
                    console.warn('No channels loaded for guild:', this.currentGuild);
                }
                
                // Restore previous value if it exists
                if (currentValue) {
                    selector.value = currentValue;
                }
            });
            
        } catch (error) {
            console.error('Failed to load guild channels:', error);
        }
    }

    async saveXPSettings(event) {
        event.preventDefault();
        
        if (!this.currentGuild) {
            this.showError('Please select a server first.');
            return;
        }

        try {
            const xpConfig = {
                guild_id: this.currentGuild,
                enabled: true,  // Default to enabled
                xp_channel: document.getElementById('xpChannel').value || null,
                level_up_message: true,  // Default to enabled  
                level_up_channel: document.getElementById('levelUpChannel').value || null,
                multiplier: parseFloat(document.getElementById('xpMultiplier').value) || 1.0
            };

            await this.apiCall(`/guild/${this.currentGuild}/xp`, 'PUT', xpConfig);
            this.showSuccess('XP settings saved successfully!');
            
        } catch (error) {
            console.error('Failed to save XP settings:', error);
            this.showError('Failed to save XP settings. Please try again.');
        }
    }

    async testLevelUpMessage() {
        if (!this.currentGuild) {
            this.showError('Please select a server first.');
            return;
        }

        try {
            const response = await this.apiCall(`/guild/${this.currentGuild}/xp/test-levelup`, 'POST');
            this.showSuccess('Test level up message sent successfully!');
        } catch (error) {
            console.error('Failed to send test message:', error);
            this.showError('Failed to send test message. Please try again.');
        }
    }

    async loadGuildMembers() {
        if (!this.currentGuild) return;

        try {
            const response = await this.apiCall(`/guild/${this.currentGuild}/members`);
            const members = response.members || [];
            
            const memberSelect = document.getElementById('memberSelect');
            memberSelect.innerHTML = '<option value="">Choose a member...</option>';
            
            if (members.length > 0) {
                members.forEach(member => {
                    const option = document.createElement('option');
                    option.value = member.id;
                    option.textContent = member.display_name || member.username;
                    memberSelect.appendChild(option);
                });
            } else {
                const option = document.createElement('option');
                option.value = '';
                option.textContent = 'No members available - Enable GUILD_MEMBERS intent in Discord Developer Portal';
                option.disabled = true;
                memberSelect.appendChild(option);
            }
            
        } catch (error) {
            console.error('Failed to load guild members:', error);
            const memberSelect = document.getElementById('memberSelect');
            memberSelect.innerHTML = '<option value="">Error loading members</option>';
        }
    }

    async loadModerationHistory() {
        if (!this.currentGuild) return;

        try {
            const response = await this.apiCall(`/guild/${this.currentGuild}/moderation/history`);
            const history = response.history || [];
            
            const historyTable = document.getElementById('moderationHistoryTable');
            historyTable.innerHTML = '';
            
            if (history.length > 0) {
                history.forEach(action => {
                    const row = document.createElement('tr');
                    const actionBadge = action.action_type === 'warning' ? 'bg-warning' : 'bg-danger';
                    row.innerHTML = `
                        <td>${action.user_id}</td>
                        <td><span class="badge ${actionBadge}">${action.action_type}</span></td>
                        <td>${new Date(action.created_at).toLocaleDateString()}</td>
                    `;
                    historyTable.appendChild(row);
                });
            } else {
                historyTable.innerHTML = '<tr><td colspan="3" class="text-center text-muted">No moderation history</td></tr>';
            }
            
        } catch (error) {
            console.error('Failed to load moderation history:', error);
            const historyTable = document.getElementById('moderationHistoryTable');
            historyTable.innerHTML = '<tr><td colspan="3" class="text-center text-muted">Error loading history</td></tr>';
        }
    }

    async loadWelcomeConfig() {
        if (!this.currentGuild) return;

        try {
            const config = await this.apiCall(`/guild/${this.currentGuild}/welcome`);
            
            document.getElementById('welcomeEnabled').checked = config.welcome_enabled || false;
            document.getElementById('welcomeChannel').value = config.welcome_channel || '';
            document.getElementById('welcomeMessage').value = config.welcome_message || 'Welcome {user} to {server}!';
            
            document.getElementById('goodbyeEnabled').checked = config.goodbye_enabled || false;
            document.getElementById('goodbyeChannel').value = config.goodbye_channel || '';
            document.getElementById('goodbyeMessage').value = config.goodbye_message || 'Goodbye {user}, thanks for being part of {server}!';
            
        } catch (error) {
            console.error('Failed to load welcome config:', error);
        }
    }

    async loadServerLogsConfig() {
        if (!this.currentGuild) return;

        try {
            const config = await this.apiCall(`/guild/${this.currentGuild}/logs`);
            
            document.getElementById('serverLogsEnabled').checked = config.enabled || false;
            document.getElementById('serverLogsChannel').value = config.channel_id || '';
            
            // Set log type toggles
            const logTypes = [
                'logMessageDelete', 'logMessageEdit', 'logMemberJoin', 'logMemberLeave',
                'logMemberUpdate', 'logVoiceStateUpdate', 'logRoleCreate', 'logRoleDelete',
                'logRoleUpdate', 'logChannelCreate', 'logChannelDelete', 'logChannelUpdate'
            ];
            
            const apiFields = [
                'message_delete', 'message_edit', 'member_join', 'member_leave',
                'member_update', 'voice_state_update', 'role_create', 'role_delete',
                'role_update', 'channel_create', 'channel_delete', 'channel_update'
            ];
            
            logTypes.forEach((elementId, index) => {
                const checkbox = document.getElementById(elementId);
                if (checkbox) {
                    checkbox.checked = config[apiFields[index]] || false;
                }
            });
            
        } catch (error) {
            console.error('Failed to load server logs config:', error);
        }
    }

    async executeModerationAction() {
        if (!this.currentGuild) {
            this.showError('Please select a server first.');
            return;
        }

        const memberId = document.getElementById('memberSelect').value;
        const action = document.getElementById('moderationAction').value;
        const reason = document.getElementById('moderationReason').value;
        const channelId = document.getElementById('moderationChannel').value;

        if (!memberId || !action) {
            this.showError('Please select a member and action.');
            return;
        }

        try {
            const actionData = {
                user_id: memberId,
                action: action,  // Changed from action_type to action
                reason: reason || 'No reason provided'
            };

            // Add channel_id if selected
            if (channelId) {
                actionData.channel_id = channelId;
            }

            if (action === 'timeout') {
                const timeoutMinutes = document.getElementById('timeoutMinutes').value;
                actionData.duration = parseInt(timeoutMinutes) || 60;
            }

            await this.apiCall(`/guild/${this.currentGuild}/moderation/action`, 'POST', actionData);
            this.showSuccess(`${action.charAt(0).toUpperCase() + action.slice(1)} executed successfully!`);
            
            // Clear form and reload history
            document.getElementById('memberSelect').value = '';
            document.getElementById('moderationAction').value = '';
            document.getElementById('moderationReason').value = '';
            document.getElementById('moderationChannel').value = '';
            document.getElementById('timeoutMinutes').value = '60';
            document.getElementById('timeoutDuration').style.display = 'none';
            
            await this.loadModerationHistory();
            
        } catch (error) {
            console.error('Failed to execute moderation action:', error);
            this.showError('Failed to execute moderation action. Please try again.');
        }
    }

    async saveWelcomeSettings(event) {
        event.preventDefault();
        
        if (!this.currentGuild) {
            this.showError('Please select a server first.');
            return;
        }

        try {
            const welcomeConfig = {
                welcome_enabled: document.getElementById('welcomeEnabled').checked,
                welcome_channel: document.getElementById('welcomeChannel').value || null,
                welcome_message: document.getElementById('welcomeMessage').value || 'Welcome {user} to {server}!',
                goodbye_enabled: document.getElementById('goodbyeEnabled').checked,
                goodbye_channel: document.getElementById('goodbyeChannel').value || null,
                goodbye_message: document.getElementById('goodbyeMessage').value || 'Goodbye {user}, thanks for being part of {server}!'
            };

            await this.apiCall(`/guild/${this.currentGuild}/welcome`, 'PUT', welcomeConfig);
            this.showSuccess('Welcome settings saved successfully!');
            
        } catch (error) {
            console.error('Failed to save welcome settings:', error);
            this.showError('Failed to save welcome settings. Please try again.');
        }
    }

    async saveServerLogsSettings(event) {
        event.preventDefault();
        
        if (!this.currentGuild) {
            this.showError('Please select a server first.');
            return;
        }

        try {
            const logsConfig = {
                enabled: document.getElementById('serverLogsEnabled').checked,
                channel_id: document.getElementById('serverLogsChannel').value || null,
                message_delete: document.getElementById('logMessageDelete').checked,
                message_edit: document.getElementById('logMessageEdit').checked,
                member_join: document.getElementById('logMemberJoin').checked,
                member_leave: document.getElementById('logMemberLeave').checked,
                member_update: document.getElementById('logMemberUpdate').checked,
                voice_state_update: document.getElementById('logVoiceStateUpdate').checked,
                role_create: document.getElementById('logRoleCreate').checked,
                role_delete: document.getElementById('logRoleDelete').checked,
                role_update: document.getElementById('logRoleUpdate').checked,
                channel_create: document.getElementById('logChannelCreate').checked,
                channel_delete: document.getElementById('logChannelDelete').checked,
                channel_update: document.getElementById('logChannelUpdate').checked
            };

            await this.apiCall(`/guild/${this.currentGuild}/logs`, 'PUT', logsConfig);
            this.showSuccess('Server logs settings saved successfully!');
            
        } catch (error) {
            console.error('Failed to save server logs settings:', error);
            this.showError('Failed to save server logs settings. Please try again.');
        }
    }

    async testWelcomeMessage() {
        if (!this.currentGuild) {
            this.showError('Please select a server first.');
            return;
        }

        try {
            await this.apiCall(`/guild/${this.currentGuild}/welcome/test`, 'POST');
            this.showSuccess('Test welcome message sent successfully!');
        } catch (error) {
            console.error('Failed to send test welcome message:', error);
            this.showError('Failed to send test welcome message. Please try again.');
        }
    }

    async testServerLog() {
        if (!this.currentGuild) {
            this.showError('Please select a server first.');
            return;
        }

        try {
            await this.apiCall(`/guild/${this.currentGuild}/logs/test`, 'POST');
            this.showSuccess('Test server log sent successfully!');
        } catch (error) {
            console.error('Failed to send test server log:', error);
            this.showError('Failed to send test server log. Please try again.');
        }
    }

    toggleAllLogs(enabled) {
        const logTypes = [
            'logMessageDelete', 'logMessageEdit', 'logMemberJoin', 'logMemberLeave',
            'logMemberUpdate', 'logVoiceStateUpdate', 'logRoleCreate', 'logRoleDelete',
            'logRoleUpdate', 'logChannelCreate', 'logChannelDelete', 'logChannelUpdate'
        ];

        logTypes.forEach(elementId => {
            const checkbox = document.getElementById(elementId);
            if (checkbox) {
                checkbox.checked = enabled;
            }
        });
    }

    showSuccess(message) {
        this.showAlert(message, 'success');
    }

    showError(message) {
        this.showAlert(message, 'danger');
    }

    showAlert(message, type) {
        // Remove existing alerts
        const existingAlerts = document.querySelectorAll('.alert');
        existingAlerts.forEach(alert => alert.remove());

        // Create new alert
        const alert = document.createElement('div');
        alert.className = `alert alert-${type} alert-dismissible fade show`;
        alert.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;

        // Insert at the top of main content
        const mainContent = document.querySelector('main');
        mainContent.insertBefore(alert, mainContent.firstChild);

        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (alert.parentNode) {
                alert.remove();
            }
        }, 5000);
    }

    logout() {
        // Clear cookies
        document.cookie = 'access_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
        window.location.href = '/';
    }

    // Navigation methods for modern sidebar
    async loadOverviewData() {
        await this.loadGuildStats();
    }

    async loadXPSettings() {
        await this.loadGuildConfig();
        await this.loadGuildChannels();
        this.populateXPSettings();
    }

    async loadModerationData() {
        await this.loadGuildMembers();
        await this.loadGuildChannels();
        await this.loadModerationHistory();
        this.populateModerationSettings();
    }

    async loadWelcomeSettings() {
        await this.loadWelcomeConfig();
        await this.loadGuildChannels();
        this.populateWelcomeSettings();
    }

    async loadLogsSettings() {
        await this.loadServerLogsConfig();
        await this.loadGuildChannels();
        this.populateLogsSettings();
    }

    populateXPSettings() {
        // Populate XP settings form with current guild config
        // This will be called when the XP Settings tab is loaded
        console.log('Populating XP settings...');
    }

    populateModerationSettings() {
        // Populate moderation settings form
        console.log('Populating moderation settings...');
    }

    populateWelcomeSettings() {
        // Populate welcome settings form
        console.log('Populating welcome settings...');
    }

    populateLogsSettings() {
        // Populate logs settings form
        console.log('Populating logs settings...');
    }
}

// Setup modern navigation for the new sidebar
function setupModernNavigation() {
    console.log('=== Setting up modern navigation ===');
    
    try {
        const navItems = document.querySelectorAll('.sidebar-nav .nav-item');
        const tabPanes = document.querySelectorAll('.tab-pane');
        
        console.log('Modern navigation - Nav items found:', navItems.length);
        console.log('Modern navigation - Tab panes found:', tabPanes.length);
        
        // Log each nav item and tab pane for debugging
        navItems.forEach((item, index) => {
            console.log(`Nav item ${index}:`, item.getAttribute('href'), item);
        });
        
        tabPanes.forEach((pane, index) => {
            console.log(`Tab pane ${index}:`, pane.id, pane);
        });
        
        if (navItems.length === 0 || tabPanes.length === 0) {
            console.error('No navigation elements found, falling back to simple navigation');
            setupSimpleNavigation();
            return;
        }
        
        // Initialize tabs - hide all except first
        tabPanes.forEach((pane, index) => {
            if (index === 0) {
                pane.style.display = 'block';
                pane.classList.add('show', 'active');
                pane.classList.remove('fade');
                console.log('✅ Initialized first tab:', pane.id);
            } else {
                pane.style.display = 'none';
                pane.classList.remove('show', 'active');
                console.log('❌ Hidden tab:', pane.id);
            }
        });
        
        // Initialize nav items - set first as active
        navItems.forEach((item, index) => {
            if (index === 0) {
                item.classList.add('active');
                console.log('✅ Set first nav active:', item.getAttribute('href'));
            } else {
                item.classList.remove('active');
            }
        });
        
        // Add click listeners with enhanced debugging
        navItems.forEach((navItem, index) => {
            const href = navItem.getAttribute('href');
            console.log(`🔗 Setting up click handler for: ${href}`);
            
            navItem.addEventListener('click', function(e) {
                e.preventDefault();
                e.stopPropagation();
                
                const targetId = href.substring(1);
                const targetPane = document.getElementById(targetId);
                
                console.log('🖱️ NAVIGATION CLICKED:', {
                    href: href,
                    targetId: targetId,
                    targetPane: targetPane,
                    targetFound: !!targetPane
                });
                
                if (!targetPane) {
                    console.error('❌ Target pane not found:', targetId);
                    return;
                }
                
                // Update nav items - remove active from all, add to clicked
                navItems.forEach(item => {
                    item.classList.remove('active');
                    console.log('➖ Removed active from:', item.getAttribute('href'));
                });
                this.classList.add('active');
                console.log('➕ Added active to:', href);
                
                // Update tab panes - hide all, show target
                tabPanes.forEach(pane => {
                    pane.style.display = 'none';
                    pane.classList.remove('show', 'active');
                    console.log('👁️ Hidden pane:', pane.id);
                });
                
                // Show target pane with enhanced visibility
                targetPane.style.display = 'block';
                targetPane.style.visibility = 'visible';
                targetPane.style.opacity = '1';
                targetPane.classList.add('show', 'active');
                targetPane.classList.remove('fade');
                
                console.log('🎯 SWITCHED TO:', {
                    paneId: targetId,
                    display: targetPane.style.display,
                    visibility: targetPane.style.visibility,
                    opacity: targetPane.style.opacity,
                    classes: targetPane.className
                });
                
                // Double-check visibility
                setTimeout(() => {
                    const rect = targetPane.getBoundingClientRect();
                    console.log('📏 Pane dimensions:', {
                        width: rect.width,
                        height: rect.height,
                        visible: rect.width > 0 && rect.height > 0
                    });
                }, 100);
            });
        });
        
        console.log('✅ Modern navigation setup completed successfully');
        
    } catch (error) {
        console.error('❌ Error in modern navigation setup:', error);
        setupSimpleNavigation();
    }
}

// Simple fallback navigation
function setupSimpleNavigation() {
    console.log('=== Setting up simple navigation fallback ===');
    
    const links = [
        { href: '#overview', target: 'overview' },
        { href: '#xp-settings', target: 'xp-settings' }, 
        { href: '#moderation', target: 'moderation' },
        { href: '#welcome', target: 'welcome' },
        { href: '#logs', target: 'logs' }
    ];
    
    links.forEach((link, index) => {
        const navItem = document.querySelector(`a[href="${link.href}"]`);
        const targetPane = document.getElementById(link.target);
        
        console.log(`Simple nav ${index}: ${link.href}`, {
            navItem: navItem ? 'FOUND' : 'NOT FOUND',
            targetPane: targetPane ? 'FOUND' : 'NOT FOUND',
            navElement: navItem,
            paneElement: targetPane
        });
        
        if (navItem && targetPane) {
            // Remove any existing click handlers
            navItem.onclick = null;
            
            // Add new click handler
            navItem.onclick = function(e) {
                e.preventDefault();
                e.stopPropagation();
                
                console.log('🖱️ SIMPLE NAVIGATION CLICKED:', link.target);
                
                // Hide all tabs and remove active from all nav items
                links.forEach(l => {
                    const pane = document.getElementById(l.target);
                    const nav = document.querySelector(`a[href="${l.href}"]`);
                    if (pane) {
                        pane.style.display = 'none';
                        pane.style.visibility = 'hidden';
                        pane.classList.remove('show', 'active');
                        console.log('👁️ Simple hidden:', l.target);
                    }
                    if (nav) {
                        nav.classList.remove('active');
                    }
                });
                
                // Show target and set active with enhanced visibility
                targetPane.style.display = 'block';
                targetPane.style.visibility = 'visible';
                targetPane.style.opacity = '1';
                targetPane.classList.add('show', 'active');
                targetPane.classList.remove('fade');
                navItem.classList.add('active');
                
                console.log('🎯 SIMPLE SWITCHED TO:', {
                    target: link.target,
                    display: targetPane.style.display,
                    visibility: targetPane.style.visibility,
                    classes: targetPane.className
                });
                
                return false;
            };
            
            // Initialize first tab
            if (index === 0) {
                targetPane.style.display = 'block';
                targetPane.style.visibility = 'visible';
                targetPane.classList.add('show', 'active');
                targetPane.classList.remove('fade');
                navItem.classList.add('active');
                console.log('✅ Simple initialized first tab:', link.target);
            } else {
                targetPane.style.display = 'none';
                targetPane.style.visibility = 'hidden';
                targetPane.classList.remove('show', 'active');
                navItem.classList.remove('active');
            }
        }
    });
    
    console.log('✅ Simple navigation setup complete');
}

// Global functions
function selectGuild() {
    dashboard.selectGuild();
}

function logout() {
    dashboard.logout();
}

// Initialize dashboard when page loads
let dashboard;
document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM loaded, initializing dashboard...');
    console.log('Browser:', navigator.userAgent);
    
    dashboard = new Dashboard();
    
    // Make dashboard globally available for debugging
    window.dashboard = dashboard;
    
    // Setup navigation with multiple approaches for reliability
    // Add a small delay for browsers that need more time to render DOM
    setTimeout(() => {
        try {
            setupModernNavigation();
            setupSimpleNavigation();
            console.log('✅ Navigation setup complete');
        } catch (error) {
            console.error('❌ Navigation setup failed:', error);
            // Try simple navigation only as last resort
            try {
                setupSimpleNavigation();
            } catch (fallbackError) {
                console.error('❌ Fallback navigation also failed:', fallbackError);
            }
        }
    }, 100);
    
    // Make setupNav globally available for debugging
    window.setupNav = setupModernNavigation;
    
    // Setup form handlers
    const xpForm = document.getElementById('xpSettingsForm');
    if (xpForm) {
        xpForm.addEventListener('submit', (e) => dashboard.saveXPSettings(e));
    }
    
    const welcomeForm = document.getElementById('welcomeSettingsForm');
    if (welcomeForm) {
        welcomeForm.addEventListener('submit', (e) => dashboard.saveWelcomeSettings(e));
    }
    
    const logsForm = document.getElementById('logsSettingsForm');
    if (logsForm) {
        logsForm.addEventListener('submit', (e) => dashboard.saveServerLogsSettings(e));
    }
    
    // Setup test buttons
    const testLevelUpBtn = document.getElementById('testLevelUpBtn');
    if (testLevelUpBtn) {
        testLevelUpBtn.addEventListener('click', () => dashboard.testLevelUpMessage());
    }
    
    const testWelcomeBtn = document.getElementById('testWelcomeBtn');
    if (testWelcomeBtn) {
        testWelcomeBtn.addEventListener('click', () => dashboard.testWelcomeMessage());
    }
    
    const testLogBtn = document.getElementById('testLogBtn');
    if (testLogBtn) {
        testLogBtn.addEventListener('click', () => dashboard.testServerLog());
    }
    
    // Setup moderation action handler
    const executeModerationBtn = document.getElementById('executeModerationBtn');
    if (executeModerationBtn) {
        executeModerationBtn.addEventListener('click', () => dashboard.executeModerationAction());
    }
    
    // Setup moderation action selector to show/hide timeout duration
    const moderationAction = document.getElementById('moderationAction');
    if (moderationAction) {
        moderationAction.addEventListener('change', (e) => {
            const timeoutDuration = document.getElementById('timeoutDuration');
            if (timeoutDuration) {
                if (e.target.value === 'timeout') {
                    timeoutDuration.style.display = 'block';
                } else {
                    timeoutDuration.style.display = 'none';
                }
            }
        });
    }
});

// Make dashboard globally available for debugging
window.dashboard = dashboard;
