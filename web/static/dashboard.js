// Maybee Dashboard JavaScript
class Dashboard {
    constructor() {
        this.currentGuild = null;
        this.dataLoaded = {};
        this.channels = null;
        this.roles = null;
        this.categories = null;
        this.members = null;
        this.pendingRequests = new Map(); // Track pending API requests to prevent duplicates
        this.user = null;
        this.guilds = [];
        this.currentLanguage = 'en';
        this.availableLanguages = [];
        this.strings = {};
        this.guildStats = null;
        this.guildConfig = null;
        this.cachedRoleMenus = null;
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

            // Use language data from backend if available, otherwise load from API
            if (window.langData && window.currentLang && window.supportedLanguages) {
                this.currentLanguage = window.currentLang;
                this.strings = window.langData;
                this.availableLanguages = window.supportedLanguages.map(code => ({
                    code: code,
                    name: code === 'en' ? 'English' : 'Français',
                    flag: code === 'en' ? '🇺🇸' : '🇫🇷'
                }));
                
                // Initialize language selector
                this.initLanguageSelector();
                
                // Update UI with translations immediately
                this.updateUILanguage();
            } else {
                // Fallback to old method
                await this.loadAvailableLanguages();
                await this.loadUserLanguage();
                await this.loadLanguageStrings();
                this.initLanguageSelector();
                this.updateUILanguage();
            }
            
            // Load user data
            await this.loadUser();
            await this.loadGuilds();
            
            // Hide loading overlay
            document.getElementById('loadingOverlay').style.display = 'none';
            document.getElementById('dashboardContent').style.display = 'block';
            
        } catch (error) {
            console.error('Initialization error:', error);
            this.showError(this.getString('errors.load_error') || 'Failed to load dashboard. Please try logging in again.');
        }
    }

    getCookie(name) {
        const value = `; ${document.cookie}`;
        const parts = value.split(`; ${name}=`);
        if (parts.length === 2) return parts.pop().split(';').shift();
    }

    setCookie(name, value, days) {
        const expires = new Date();
        expires.setTime(expires.getTime() + (days * 24 * 60 * 60 * 1000));
        document.cookie = `${name}=${value};expires=${expires.toUTCString()};path=/`;
    }

    async apiCall(endpoint, method = 'GET', data = null) {
        // Create request key for deduplication
        const requestKey = `${method}:${endpoint}:${JSON.stringify(data)}`;
        
        // If same request is already pending, wait for it
        if (this.pendingRequests.has(requestKey)) {
            console.log(`⏳ Waiting for pending request: ${requestKey}`);
            return await this.pendingRequests.get(requestKey);
        }
        
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

        // Create the request promise and store it
        const requestPromise = (async () => {
            try {
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
            } finally {
                // Remove from pending requests when done
                this.pendingRequests.delete(requestKey);
            }
        })();
        
        // Store the promise for deduplication
        this.pendingRequests.set(requestKey, requestPromise);
        
        return await requestPromise;
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
            guildSelector.innerHTML = `<option value="">${this.getString('navigation.select_server')}</option>`;
            
            this.guilds.forEach(guild => {
                const option = document.createElement('option');
                option.value = guild.id;
                option.textContent = guild.name;
                guildSelector.appendChild(option);
            });
            
            if (this.guilds.length === 0) {
                this.showError(this.getString('errors.no_guilds') || 'No manageable servers found. Make sure the bot is in your server and you have administrator permissions.');
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
            // Save language preference to server
            await this.apiCall('/user/language', 'PUT', { language: languageCode });
            
            // Set language cookie for persistence
            this.setCookie('language', languageCode, 365);
            
            // Update current language
            this.currentLanguage = languageCode;
            
            // Load new language strings
            await this.loadLanguageStrings();
            
            // Update UI
            this.updateUILanguage();
            this.initLanguageSelector();
            
            // Show success message
            this.showSuccess(this.getString('language.language_changed') || 'Language changed successfully!');
            
            // Update URL to reflect language change (optional, for consistency)
            const url = new URL(window.location);
            url.searchParams.set('lang', languageCode);
            window.history.replaceState({}, '', url);
            
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
            'role-menus': document.querySelector('a[href="#role-menus"]'),
            'logs': document.querySelector('a[href="#logs"]'),
            'tickets': document.querySelector('a[href="#tickets"]'),
            'embed': document.querySelector('a[href="#embed"]')
        };

        if (navigationElements.overview) {
            navigationElements.overview.innerHTML = `
                <div class="nav-icon"><i class="fas fa-tachometer-alt"></i></div>
                <span class="nav-text">${this.getString('navigation.overview')}</span>
            `;
        }
        if (navigationElements['xp-settings']) {
            navigationElements['xp-settings'].innerHTML = `
                <div class="nav-icon"><i class="fas fa-trophy"></i></div>
                <span class="nav-text">${this.getString('navigation.xp_system')}</span>
            `;
        }
        if (navigationElements.moderation) {
            navigationElements.moderation.innerHTML = `
                <div class="nav-icon"><i class="fas fa-shield-alt"></i></div>
                <span class="nav-text">${this.getString('navigation.moderation')}</span>
            `;
        }
        if (navigationElements.welcome) {
            navigationElements.welcome.innerHTML = `
                <div class="nav-icon"><i class="fas fa-door-open"></i></div>
                <span class="nav-text">${this.getString('navigation.welcome_system')}</span>
            `;
        }
        if (navigationElements['role-menus']) {
            navigationElements['role-menus'].innerHTML = `
                <div class="nav-icon"><i class="fas fa-list"></i></div>
                <span class="nav-text">${this.getString('navigation.role_menus')}</span>
            `;
        }
        if (navigationElements.logs) {
            navigationElements.logs.innerHTML = `
                <div class="nav-icon"><i class="fas fa-file-alt"></i></div>
                <span class="nav-text">${this.getString('navigation.server_logs')}</span>
            `;
        }
        if (navigationElements.tickets) {
            navigationElements.tickets.innerHTML = `
                <div class="nav-icon"><i class="fas fa-ticket-alt"></i></div>
                <span class="nav-text">${this.getString('navigation.ticket_system')}</span>
            `;
        }
        if (navigationElements.embed) {
            navigationElements.embed.innerHTML = `
                <div class="nav-icon"><i class="fas fa-code"></i></div>
                <span class="nav-text">${this.getString('navigation.embed_system')}</span>
            `;
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

        // If switching to a different guild, clear all cached data
        if (this.currentGuild && this.currentGuild !== guildId) {
            console.log('🔄 Switching guilds - clearing cached data');
            this.channels = null;
            this.roles = null;
            this.categories = null;
            this.members = null;
            this.guildStats = null;
            this.guildConfig = null;
            this.pendingRequests.clear(); // Clear pending requests
        }

        this.currentGuild = guildId;
        
        try {
            // Use bulk endpoint to load essential data in one request
            console.log('� Loading essential guild data via bulk endpoint...');
            const bulkData = await this.apiCall(`/guild/${this.currentGuild}/bulk`);
            
            // Cache the loaded data
            this.guildConfig = bulkData.config;
            this.channels = bulkData.channels;
            this.guildStats = bulkData.stats;
            this.levelRoles = bulkData.level_roles || [];
            
            // Update config form
            this.updateConfigForm(bulkData.config);
            
            // Update channel selectors
            this.updateChannelSelectors(bulkData.channels);
            
            // Update level roles display
            await this.updateLevelRolesDisplay();
            
            // Load members data to properly display user names in stats
            console.log('🔄 Loading members data for user display names...');
            await this.loadGuildMembers();
            
            console.log('👥 Members loaded, now updating stats display...');
            console.log('📊 Stats data to display:', bulkData.stats);
            
            // Update stats display with proper user names
            await this.updateStatsDisplayAsync(bulkData.stats);
            
            console.log('✅ Stats display updated successfully');
            
            // Mark essential data as loaded
            this.dataLoaded = {
                channels: true,
                config: true,
                stats: true,
                level_roles: true,
                roles: false,
                categories: false,
                members: true,
                moderation: false,
                welcome: false,
                logs: false,
                roleMenus: false,
                tickets: false
            };
            
            console.log('✅ Essential guild data loaded via bulk endpoint - other sections will load when accessed');
            
        } catch (error) {
            console.error('Failed to load guild data:', error);
            this.showError(this.getString('messages.server_data_error') || 'Failed to load server data.');
        }
    }

    updateConfigForm(config) {
        // Update XP settings form
        document.getElementById('xpEnabled').checked = config.xp_enabled !== false;
        document.getElementById('levelUpMessage').checked = config.level_up_message !== false;
        
        if (config.xp_channel) {
            document.getElementById('xpChannel').value = config.xp_channel;
        }
        if (config.level_up_channel) {
            document.getElementById('levelUpChannel').value = config.level_up_channel;
        }
    }

    updateStatsDisplay(stats) {
        // Update overview cards
        document.getElementById('totalMembers').textContent = stats.total_members?.toLocaleString() || '0';
        document.getElementById('totalXP').textContent = stats.total_xp?.toLocaleString() || '0';
        document.getElementById('avgLevel').textContent = stats.average_level || '0';
        document.getElementById('recentActivity').textContent = stats.recent_activity?.toLocaleString() || '0';
        
        // Update top users table with just user IDs (fallback)
        const topUsersTable = document.getElementById('topUsersTable');
        if (stats.top_users && stats.top_users.length > 0) {
            topUsersTable.innerHTML = '';
            stats.top_users.forEach((user, index) => {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td><span class="badge bg-primary">#${index + 1}</span></td>
                    <td>${this.getString('overview.user_id')}: ${user.user_id}</td>
                    <td><span class="badge bg-success">Level ${user.level}</span></td>
                    <td>${user.xp?.toLocaleString() || '0'} XP</td>
                `;
                topUsersTable.appendChild(row);
            });
        } else {
            topUsersTable.innerHTML = `<tr><td colspan="4" class="text-center text-muted">${this.getString('overview.no_data')}</td></tr>`;
        }
    }

    async updateStatsDisplayAsync(stats) {
        console.log('🎯 updateStatsDisplayAsync called with:', stats);
        
        try {
            // Update overview cards
            console.log('📊 Updating overview cards...');
            document.getElementById('totalMembers').textContent = stats.total_members?.toLocaleString() || '0';
            document.getElementById('totalXP').textContent = stats.total_xp?.toLocaleString() || '0';
            document.getElementById('avgLevel').textContent = stats.average_level || '0';
            document.getElementById('recentActivity').textContent = stats.recent_activity?.toLocaleString() || '0';
            console.log('✅ Overview cards updated');
            
            // Update top users table with proper display names
            const topUsersTable = document.getElementById('topUsersTable');
            console.log('👤 Top users table element:', topUsersTable ? 'Found' : 'NOT FOUND');
            
            if (stats.top_users && stats.top_users.length > 0) {
                console.log('🔄 Processing top users with member data:', stats.top_users);
                topUsersTable.innerHTML = '';
                for (const [index, user] of stats.top_users.entries()) {
                    console.log(`Processing user ${index + 1}:`, user);
                    console.log(`🔍 user.user_id:`, user.user_id, 'type:', typeof user.user_id);
                    const row = document.createElement('tr');
                    // Ensure user_id stays as string
                    const userId = String(user.user_id);
                    console.log(`🔍 After String conversion:`, userId, 'type:', typeof userId);
                    const displayName = await this.getUserDisplayNameAsync(userId);
                    console.log(`User ${index + 1}: ID=${userId}, Name=${displayName}`);
                    row.innerHTML = `
                        <td><span class="badge bg-primary">#${index + 1}</span></td>
                        <td>${displayName}</td>
                        <td><span class="badge bg-success">Level ${user.level}</span></td>
                        <td>${user.xp?.toLocaleString() || '0'} XP</td>
                    `;
                    topUsersTable.appendChild(row);
                }
                console.log('✅ Top users table updated successfully');
            } else {
                console.log('📭 No top users data, showing empty state');
                topUsersTable.innerHTML = `<tr><td colspan="4" class="text-center text-muted">${this.getString('overview.no_data')}</td></tr>`;
            }
        } catch (error) {
            console.error('❌ Error in updateStatsDisplayAsync:', error);
            throw error;
        }
    }

    updateChannelSelectors(channels) {
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
            if (channels && channels.length > 0) {
                channels.forEach(channel => {
                    const option = document.createElement('option');
                    option.value = channel.id;
                    option.textContent = `#${channel.name}`;
                    selector.appendChild(option);
                });
            }
            
            // Restore previous value if it exists
            if (currentValue) {
                selector.value = currentValue;
            }
        });
    }

    // Level Roles Management
    async updateLevelRolesDisplay() {
        console.log('🎖️ Updating level roles display with:', this.levelRoles);
        
        const levelRolesList = document.getElementById('levelRolesList');
        if (!levelRolesList) return;
        
        // Load roles if not already loaded
        if (!this.roles) {
            console.log('🔄 Loading roles for level roles display...');
            await this.loadGuildRoles();
        }
        
        levelRolesList.innerHTML = '';
        
        if (!this.levelRoles || this.levelRoles.length === 0) {
            levelRolesList.innerHTML = `
                <div class="level-role-empty">
                    <i class="fas fa-medal"></i>
                    <p>No level roles configured yet. Click "Add Level Role" to get started!</p>
                </div>
            `;
            return;
        }
        
        this.levelRoles.forEach(levelRole => {
            this.addLevelRoleItem(levelRole);
        });
    }

    addLevelRoleItem(levelRole = null) {
        const levelRolesList = document.getElementById('levelRolesList');
        const levelRoleId = levelRole ? levelRole.level : `new-${Date.now()}`;
        const isNew = !levelRole;
        
        const levelRoleItem = document.createElement('div');
        levelRoleItem.className = 'level-role-item';
        levelRoleItem.setAttribute('data-level-role-id', levelRoleId);
        
        if (isNew) {
            // Edit mode for new level role
            levelRoleItem.innerHTML = `
                <div class="level-role-grid">
                    <input type="number" class="level-role-level" 
                           placeholder="Level" min="1" value="">
                    <select class="level-role-role">
                        <option value="">Select a role...</option>
                    </select>
                </div>
                <div class="level-role-actions">
                    <button class="level-role-btn save" onclick="dashboard.saveLevelRole('${levelRoleId}')">
                        <i class="fas fa-check"></i>
                    </button>
                    <button class="level-role-btn delete" onclick="dashboard.handleRemoveLevelRole('${levelRoleId}')">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
            `;
            
            // Populate roles dropdown
            const roleSelect = levelRoleItem.querySelector('.level-role-role');
            this.loadRolesForLevelRole(roleSelect);
        } else {
            // Display mode for existing level role
            const roleName = this.getRoleName(levelRole.role_id);
            levelRoleItem.innerHTML = `
                <div class="level-role-display">
                    <div class="level-role-badge">
                        <i class="fas fa-star"></i>
                        ${levelRole.level}
                    </div>
                    <div class="level-role-name">${roleName}</div>
                </div>
                <div class="level-role-actions">
                    <button class="level-role-btn" onclick="dashboard.editLevelRole('${levelRoleId}')">
                        <i class="fas fa-edit"></i>
                    </button>
                    <button class="level-role-btn delete" onclick="dashboard.deleteLevelRole('${levelRoleId}')">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            `;
        }
        
        levelRolesList.appendChild(levelRoleItem);
        
        // Clear empty state if it exists
        const emptyState = levelRolesList.querySelector('.level-role-empty');
        if (emptyState) {
            emptyState.remove();
        }
    }

    async loadRolesForLevelRole(roleSelect, selectedRoleId = null) {
        if (!this.currentGuild) {
            console.log('❌ No current guild for level role loading');
            return;
        }

        try {
            console.log(`📡 Fetching roles for level role dropdown in guild ${this.currentGuild}`);
            const response = await this.apiCall(`/guild/${this.currentGuild}/roles`);
            const roles = response.roles || [];
            console.log(`✅ Received ${roles.length} roles for level role dropdown`);
            
            roleSelect.innerHTML = '<option value="">Select a role...</option>';
            
            roles.forEach(role => {
                if (role.name !== '@everyone' && !role.managed) {  // Skip @everyone and bot roles
                    const option = document.createElement('option');
                    option.value = role.id;
                    option.textContent = role.name;
                    
                    if (selectedRoleId && String(role.id) === String(selectedRoleId)) {
                        option.selected = true;
                        console.log(`✅ Pre-selected role: ${role.name} (${role.id})`);
                    }
                    roleSelect.appendChild(option);
                }
            });
            console.log(`✅ Added roles to level role dropdown`);
        } catch (error) {
            console.error(`❌ Failed to load roles for level role dropdown:`, error);
            roleSelect.innerHTML = '<option value="">Error loading roles...</option>';
        }
    }

    getRoleName(roleId) {
        if (!this.roles) return `Role ID: ${roleId}`;
        const role = this.roles.find(r => r.id === roleId);
        if (role) {
            return `${role.name} <small class="text-muted">(${roleId})</small>`;
        }
        return `Role ID: ${roleId}`;
    }

    async saveLevelRole(levelRoleId) {
        const levelRoleItem = document.querySelector(`[data-level-role-id="${levelRoleId}"]`);
        const levelInput = levelRoleItem.querySelector('.level-role-level');
        const roleSelect = levelRoleItem.querySelector('.level-role-role');
        
        const level = parseInt(levelInput.value);
        const roleId = roleSelect.value;
        
        if (!level || level < 1) {
            this.showError('Level must be 1 or higher');
            return;
        }
        
        if (!roleId) {
            this.showError('Please select a role');
            return;
        }
        
        try {
            const isNew = levelRoleId.startsWith('new-');
            
            if (isNew) {
                // Create new level role
                await this.apiCall(`/guild/${this.currentGuild}/level-roles`, 'POST', {
                    level: level,
                    role_id: roleId
                });
                this.showSuccess('Level role created successfully!');
            } else {
                // Update existing level role - find the original level
                const originalLevelRole = this.levelRoles.find(lr => lr.level == levelRoleId || lr.guild_id + '_' + lr.level == levelRoleId);
                const originalLevel = originalLevelRole ? originalLevelRole.level : levelRoleId;
                
                await this.apiCall(`/guild/${this.currentGuild}/level-roles/${originalLevel}`, 'PUT', {
                    level: level,
                    role_id: roleId
                });
                this.showSuccess('Level role updated successfully!');
            }
            
            // Reload level roles
            await this.loadLevelRoles();
            
        } catch (error) {
            console.error('Failed to save level role:', error);
            this.showError('Failed to save level role: ' + (error.detail || error.message || 'Unknown error'));
        }
    }

    editLevelRole(levelRoleId) {
        const levelRole = this.levelRoles.find(lr => lr.level == levelRoleId);
        if (!levelRole) return;
        
        const levelRoleItem = document.querySelector(`[data-level-role-id="${levelRoleId}"]`);
        
        // Switch to edit mode
        levelRoleItem.innerHTML = `
            <div class="level-role-grid">
                <input type="number" class="level-role-level" 
                       placeholder="Level" min="1" value="${levelRole.level}">
                <select class="level-role-role">
                    <option value="">Select a role...</option>
                </select>
            </div>
            <div class="level-role-actions">
                <button class="level-role-btn save" onclick="dashboard.saveLevelRole('${levelRoleId}')">
                    <i class="fas fa-check"></i>
                </button>
                <button class="level-role-btn delete" onclick="dashboard.cancelEditLevelRole('${levelRoleId}')">
                    <i class="fas fa-times"></i>
                </button>
            </div>
        `;
        
        // Populate roles dropdown
        const roleSelect = levelRoleItem.querySelector('.level-role-role');
        this.loadRolesForLevelRole(roleSelect, levelRole.role_id);
    }

    cancelEditLevelRole(levelRoleId) {
        const levelRole = this.levelRoles.find(lr => lr.id == levelRoleId);
        if (!levelRole) return;
        
        // Recreate the display mode
        const levelRoleItem = document.querySelector(`[data-level-role-id="${levelRoleId}"]`);
        const roleName = this.getRoleName(levelRole.role_id);
        
        levelRoleItem.innerHTML = `
            <div class="level-role-display">
                <div class="level-role-badge">
                    <i class="fas fa-star"></i>
                    ${levelRole.level}
                </div>
                <div class="level-role-name">${roleName}</div>
            </div>
            <div class="level-role-actions">
                <button class="level-role-btn" onclick="dashboard.editLevelRole('${levelRoleId}')">
                    <i class="fas fa-edit"></i>
                </button>
                <button class="level-role-btn delete" onclick="dashboard.deleteLevelRole('${levelRoleId}')">
                    <i class="fas fa-trash"></i>
                </button>
            </div>
        `;
    }

    async deleteLevelRole(levelRoleId) {
        if (!confirm('Are you sure you want to delete this level role?')) return;
        
        try {
            // Find the level for this level role
            const levelRole = this.levelRoles.find(lr => lr.level == levelRoleId || lr.guild_id + '_' + lr.level == levelRoleId);
            const level = levelRole ? levelRole.level : levelRoleId;
            
            await this.apiCall(`/guild/${this.currentGuild}/level-roles/${level}`, 'DELETE');
            this.showSuccess('Level role deleted successfully!');
            
            // Reload level roles
            await this.loadLevelRoles();
            
        } catch (error) {
            console.error('Failed to delete level role:', error);
            this.showError('Failed to delete level role: ' + (error.detail || error.message || 'Unknown error'));
        }
    }

    // Wrapper function to handle async removeLevelRoleItem from onclick
    handleRemoveLevelRole(levelRoleId) {
        this.removeLevelRoleItem(levelRoleId).catch(error => {
            console.error('Failed to remove level role item:', error);
            this.showError('Failed to remove level role: ' + (error.message || 'Unknown error'));
        });
    }

    async removeLevelRoleItem(levelRoleId) {
        const levelRoleItem = document.querySelector(`[data-level-role-id="${levelRoleId}"]`);
        if (levelRoleItem) {
            levelRoleItem.remove();
        }
        
        // Show empty state if no items left
        const levelRolesList = document.getElementById('levelRolesList');
        if (levelRolesList.children.length === 0) {
            await this.updateLevelRolesDisplay();
        }
    }

    async loadLevelRoles() {
        if (!this.currentGuild) return;
        
        try {
            const response = await this.apiCall(`/guild/${this.currentGuild}/level-roles`);
            this.levelRoles = response.level_roles || [];
            await this.updateLevelRolesDisplay();
        } catch (error) {
            console.error('Failed to load level roles:', error);
            this.levelRoles = [];
            await this.updateLevelRolesDisplay();
        }
    }

    // Helper function to get user display name from user ID
    async getUserDisplayNameAsync(userId) {
        console.log('Getting display name for user ID:', userId, typeof userId);
        console.log('Available members:', this.members?.length || 0);
        
        if (!this.members || this.members.length === 0) {
            console.log('No members data available');
            return `${this.getString('overview.user_id')}: ${userId}`;
        }
        
        // Convert userId to string for comparison since API might return different types
        const userIdStr = String(userId);
        console.log('Looking for user ID (as string):', userIdStr);
        
        // Find exact match
        const member = this.members.find(member => String(member.id) === userIdStr);
        
        if (member) {
            const displayName = member.display_name || member.username;
            console.log(`Found member: ${displayName} for ID: ${userId}`);
            return displayName;
        }
        
        // If not found in members, try to get user info from API
        try {
            console.log(`Member not found locally, trying API for ID: ${userId}`);
            // Ensure userId is treated as string to prevent precision loss
            const userIdStr = String(userId);
            const userInfo = await this.apiCall(`/user/${userIdStr}`);
            if (userInfo && (userInfo.username || userInfo.display_name)) {
                const displayName = userInfo.display_name || userInfo.username;
                console.log(`Found user via API: ${displayName} for ID: ${userId}`);
                return `${displayName} (ex-member)`;
            }
        } catch (error) {
            console.log(`Failed to get user info from API for ID: ${userId}`, error);
        }
        
        console.log(`Member not found for ID: ${userId}`);
        return `${this.getString('overview.user_id')}: ${userId}`;
    }

    // Synchronous version for backward compatibility
    getUserDisplayName(userId) {
        const userIdStr = String(userId);
        const member = this.members?.find(member => String(member.id) === userIdStr);
        
        if (member) {
            return member.display_name || member.username;
        }
        
        return `${this.getString('overview.user_id')}: ${userId}`;
    }

    async loadGuildStats() {
        // Return cached data if available and not stale
        if (this.guildStats && this.dataLoaded?.stats) {
            console.log('✅ Using cached guild stats');
            return;
        }
        
        if (!this.currentGuild) return;

        try {
            console.log('🔄 Loading guild stats...');
            const stats = await this.apiCall(`/guild/${this.currentGuild}/stats`);
            this.guildStats = stats; // Cache the stats
            
            if (this.dataLoaded) this.dataLoaded.stats = true;
            
            // Update overview cards
            document.getElementById('totalMembers').textContent = stats.total_members?.toLocaleString() || '0';
            document.getElementById('totalXP').textContent = stats.total_xp?.toLocaleString() || '0';
            document.getElementById('avgLevel').textContent = stats.average_level || '0';
            document.getElementById('recentActivity').textContent = stats.recent_activity?.toLocaleString() || '0';
            
            // Update top users table
            const topUsersTable = document.getElementById('topUsersTable');
            topUsersTable.innerHTML = '';
            
            if (stats.top_users && stats.top_users.length > 0) {
                console.log('Processing top users:', stats.top_users);
                topUsersTable.innerHTML = '';
                for (const [index, user] of stats.top_users.entries()) {
                    const row = document.createElement('tr');
                    const displayName = await this.getUserDisplayNameAsync(user.user_id);
                    console.log(`User ${index + 1}: ID=${user.user_id}, Name=${displayName}`);
                    row.innerHTML = `
                        <td><span class="badge bg-primary">#${index + 1}</span></td>
                        <td>${displayName}</td>
                        <td><span class="badge bg-success">Level ${user.level}</span></td>
                        <td>${user.xp?.toLocaleString() || '0'} XP</td>
                    `;
                    topUsersTable.appendChild(row);
                }
            } else {
                topUsersTable.innerHTML = `<tr><td colspan="4" class="text-center text-muted">${this.getString('overview.no_data')}</td></tr>`;
            }
            
        } catch (error) {
            console.error('Failed to load guild stats:', error);
        }
    }

    async loadGuildConfig() {
        // Return cached data if available
        if (this.guildConfig && this.dataLoaded?.config) {
            console.log('✅ Using cached guild config');
            this.updateConfigForm(this.guildConfig);
            return;
        }
        
        if (!this.currentGuild) return;

        try {
            console.log('🔄 Loading guild config...');
            const config = await this.apiCall(`/guild/${this.currentGuild}/config`);
            this.guildConfig = config;
            
            if (this.dataLoaded) this.dataLoaded.config = true;
            
            this.updateConfigForm(config);
            
        } catch (error) {
            console.error('Failed to load guild config:', error);
        }
    }

    async loadGuildChannels() {
        // Return cached data if available and not stale
        if (this.channels && this.dataLoaded?.channels) {
            console.log('✅ Using cached channels data');
            return;
        }
        
        if (!this.currentGuild) return;

        try {
            console.log('Loading channels for guild:', this.currentGuild);
            this.channels = await this.apiCall(`/guild/${this.currentGuild}/channels`);
            console.log('Loaded channels:', this.channels);
            
            if (this.dataLoaded) this.dataLoaded.channels = true;
            
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

    async loadGuildRoles() {
        if (!this.currentGuild) return;

        try {
            console.log('Loading roles for guild:', this.currentGuild);
            const response = await this.apiCall(`/guild/${this.currentGuild}/roles`);
            this.roles = response.roles || [];
            console.log('Loaded roles:', this.roles);
            
            // Update role selector for auto-role assignment
            const roleSelect = document.getElementById('roleSelect');
            if (roleSelect) {
                const currentValue = roleSelect.value;
                
                // Clear existing options except the first one
                while (roleSelect.children.length > 1) {
                    roleSelect.removeChild(roleSelect.lastChild);
                }
                
                // Add role options (exclude @everyone and bot roles)
                if (this.roles && this.roles.length > 0) {
                    this.roles.forEach(role => {
                        if (role.name !== '@everyone' && !role.managed) {  // Skip @everyone and bot roles
                            const option = document.createElement('option');
                            option.value = role.id;
                            option.textContent = role.name;
                            roleSelect.appendChild(option);
                        }
                    });
                } else {
                    console.warn('No roles loaded for guild:', this.currentGuild);
                }
            }
            
        } catch (error) {
            console.error('Failed to load guild roles:', error);
            this.roles = [];
        }
    }

    async loadGuildCategories() {
        if (!this.currentGuild) return;

        try {
            console.log('Loading categories for guild:', this.currentGuild);
            this.categories = await this.apiCall(`/guild/${this.currentGuild}/categories`);
            console.log('Loaded categories:', this.categories);
        } catch (error) {
            console.error('Failed to load guild categories:', error);
            this.categories = [];
        }
    }

    async saveXPSettings(event) {
        event.preventDefault();
        
        if (!this.currentGuild) {
            this.showError(this.getString('messages.please_select_server') || 'Please select a server first.');
            return;
        }

        try {
            const xpConfig = {
                guild_id: this.currentGuild,
                enabled: true,  // Default to enabled
                xp_channel: document.getElementById('xpChannel').value || null,
                level_up_message: true,  // Default to enabled  
                level_up_channel: document.getElementById('levelUpChannel').value || null
            };

            await this.apiCall(`/guild/${this.currentGuild}/xp`, 'PUT', xpConfig);
            this.showSuccess(this.getString('messages.xp_settings_saved') || 'XP settings saved successfully!');
            
        } catch (error) {
            console.error('Failed to save XP settings:', error);
            this.showError(this.getString('messages.save_error') || 'Failed to save XP settings. Please try again.');
        }
    }

    async testLevelUpMessage() {
        if (!this.currentGuild) {
            this.showError(this.getString('messages.please_select_server') || 'Please select a server first.');
            return;
        }

        try {
            const response = await this.apiCall(`/guild/${this.currentGuild}/xp/test-levelup`, 'POST');
            this.showSuccess(this.getString('messages.test_success') || 'Test level up message sent successfully!');
        } catch (error) {
            console.error('Failed to send test message:', error);
            this.showError(this.getString('messages.test_error') || 'Failed to send test message. Please try again.');
        }
    }

    async resetServerXP() {
        if (!this.currentGuild) {
            this.showError(this.getString('messages.please_select_server') || 'Please select a server first.');
            return;
        }

        // Show confirmation dialog
        const confirmed = confirm(
            '⚠️ WARNING: This will permanently delete ALL XP data for this server!\n\n' +
            'This includes:\n' +
            '• All user XP and levels\n' +
            '• XP history records\n' +
            '• Level role assignments\n' +
            '• XP multipliers\n\n' +
            'This action cannot be undone!\n\n' +
            'Are you sure you want to reset all XP data?'
        );

        if (!confirmed) {
            return;
        }

        // Second confirmation
        const doubleConfirmed = confirm(
            'FINAL CONFIRMATION\n\n' +
            'This will DELETE ALL XP DATA for this server permanently.\n\n' +
            'Type "DELETE" and click OK to confirm:'
        );

        if (!doubleConfirmed) {
            return;
        }

        try {
            const response = await this.apiCall(`/guild/${this.currentGuild}/xp/reset`, 'POST');
            
            if (response.success) {
                this.showSuccess(
                    `✅ XP Reset Complete!\n\n` +
                    `Successfully deleted:\n` +
                    `• ${response.deleted_records} user XP records\n` +
                    `• All XP history records\n` +
                    `• All level role assignments\n` +
                    `• All XP multipliers\n\n` +
                    `All users will start fresh with 0 XP!`
                );
                
                // Refresh the page to show updated data
                setTimeout(() => {
                    location.reload();
                }, 2000);
            } else {
                this.showError('Failed to reset XP data: ' + (response.error || 'Unknown error'));
            }
        } catch (error) {
            console.error('Failed to reset XP data:', error);
            this.showError('Failed to reset XP data. Please try again.');
        }
    }

    // Role Menu Management Methods
    async loadRoleMenus() {
        console.log(`🔄 Loading role menus for guild: ${this.currentGuild}`);
        if (!this.currentGuild) {
            console.log('❌ No current guild set');
            return;
        }

        try {
            console.log(`📡 Making API call to get role menus`);
            const response = await this.apiCall(`/guild/${this.currentGuild}/role-menus`);
            console.log(`✅ API call successful, received ${response.menus?.length || 0} role menus`);
            this.displayRoleMenus(response.menus || []);
            
            if (this.dataLoaded) this.dataLoaded.roleMenus = true;
        } catch (error) {
            console.error('❌ Failed to load role menus:', error);
            this.showError('Failed to load role menus. Please try again.');
        }
    }

    async loadRoleMenuData() {
        // Check if already loaded
        if (this.dataLoaded?.roleMenus) {
            console.log('✅ Role menu data already loaded');
            return;
        }
        
        console.log('🔄 Loading role menu data...');
        await this.loadRoleMenus();
    }

    displayRoleMenus(menus) {
        console.log(`🎨 Displaying ${menus.length} role menus`);
        
        // Store the menus data for later use
        this.cachedRoleMenus = menus;
        
        // Check if role menus tab is currently active (Bootstrap 5 uses both 'active' and 'show')
        const roleMenusTab = document.getElementById('role-menus');
        const isTabActive = roleMenusTab && (
            roleMenusTab.classList.contains('active') || 
            roleMenusTab.classList.contains('show') ||
            (roleMenusTab.classList.contains('active') && roleMenusTab.classList.contains('show'))
        );
        
        console.log('🔍 Tab state check:', {
            tabExists: !!roleMenusTab,
            isActive: isTabActive,
            hasActiveClass: roleMenusTab?.classList.contains('active'),
            hasShowClass: roleMenusTab?.classList.contains('show'),
            tabClasses: roleMenusTab ? Array.from(roleMenusTab.classList) : null
        });
        
        // Always try to render if we have the tab element, regardless of active state
        // This will help us debug what's happening
        if (!roleMenusTab) {
            console.log('📋 Role menus tab not found, caching data for later render');
            return;
        }
        
        // Try to render immediately, but also cache for later
        this.renderRoleMenusNow(menus);
    }
    
    renderRoleMenusNow(menus) {
        console.log(`🎨 Rendering ${menus.length} role menus now`);
        
        const menusList = document.getElementById('roleMenusList');
        const emptyState = document.getElementById('roleMenusEmpty');
        
        // Add comprehensive debugging
        console.log('🔍 DOM element search:', {
            menusList: menusList ? 'Found' : 'Not found',
            emptyState: emptyState ? 'Found' : 'Not found',
            domReady: document.readyState,
            allRoleMenusElements: document.querySelectorAll('[id*="roleMenus"]').length,
            allTabPanes: document.querySelectorAll('.tab-pane').length,
            activeTabPanes: document.querySelectorAll('.tab-pane.active').length,
            currentTab: document.querySelector('.tab-pane.active')?.id || 'none'
        });
        
        // Check if elements exist but maybe have different IDs
        const allElements = document.querySelectorAll('*[id]');
        const roleMenusRelated = Array.from(allElements).filter(el => 
            el.id.toLowerCase().includes('rolemenu') || el.id.toLowerCase().includes('role-menu')
        );
        console.log('🔍 All role menu related elements:', roleMenusRelated.map(el => ({id: el.id, tagName: el.tagName})));
        
        // Add null checks to prevent errors
        if (!menusList || !emptyState) {
            console.error('❌ Role menus DOM elements not found:', {
                menusList: !!menusList,
                emptyState: !!emptyState,
                domReady: document.readyState,
                roleMenusTabExists: !!document.querySelector('#role-menus'),
                roleMenusTabActive: !!document.querySelector('#role-menus.active'),
                bootstrap5TabActive: !!document.querySelector('#role-menus.show.active'),
                allTabsWithShow: document.querySelectorAll('.tab-pane.show').length
            });
            
            // Try again with a small delay in case DOM is still loading
            console.log('🔄 Retrying DOM element search in 100ms...');
            setTimeout(() => {
                const retryMenusList = document.getElementById('roleMenusList');
                const retryEmptyState = document.getElementById('roleMenusEmpty');
                
                console.log('🔄 Retry DOM search results:', {
                    menusList: !!retryMenusList,
                    emptyState: !!retryEmptyState,
                    currentActiveTab: document.querySelector('.tab-pane.active, .tab-pane.show')?.id || 'none'
                });
                
                if (retryMenusList && retryEmptyState) {
                    console.log('✅ Found DOM elements on retry, rendering now');
                    this.renderRoleMenusList(menus, retryMenusList, retryEmptyState);
                } else {
                    console.error('❌ Still cannot find DOM elements after retry');
                }
            }, 100);
            
            return;
        }
        
        this.renderRoleMenusList(menus, menusList, emptyState);
    }
    
    // Method to check if role menus tab is active and render cached data
    checkAndRenderCachedRoleMenus() {
        const roleMenusTab = document.getElementById('role-menus');
        const isTabActive = roleMenusTab && roleMenusTab.classList.contains('active');
        
        if (isTabActive && this.cachedRoleMenus) {
            console.log('🔄 Tab is active and cached data available, rendering now');
            this.renderRoleMenusNow(this.cachedRoleMenus);
            return true;
        }
        
        return false;
    }
    
    // Force render role menus regardless of tab state (for debugging/manual refresh)
    forceRenderRoleMenus() {
        console.log('🔧 Force rendering role menus...');
        if (this.cachedRoleMenus) {
            console.log(`📋 Found ${this.cachedRoleMenus.length} cached role menus`);
            this.renderRoleMenusNow(this.cachedRoleMenus);
        } else {
            console.log('📡 No cached data, loading from API...');
            this.loadRoleMenus();
        }
    }
    
    renderRoleMenusList(menus, menusList, emptyState) {
        
        if (menus.length === 0) {
            console.log('📭 No menus to display, showing empty state');
            emptyState.style.display = 'block';
            menusList.innerHTML = '';
            return;
        }
        
        console.log('📝 Generating HTML for menus');
        emptyState.style.display = 'none';
        
        menusList.innerHTML = menus.map(menu => {
            console.log(`  - Menu: ${menu.title} (ID: ${menu.id})`);
            return `
            <div class="role-menu-item" data-menu-id="${menu.id}">
                <div class="role-menu-header">
                    <div class="role-menu-info">
                        <h4 class="role-menu-title">${this.escapeHtml(menu.title)}</h4>
                        <p class="role-menu-description">${this.escapeHtml(menu.description || 'No description')}</p>
                        <div class="role-menu-meta">
                            <span class="meta-item">
                                <i class="fas fa-hashtag"></i>
                                Channel: ${menu.channel_name || 'Unknown Channel'}
                            </span>
                            <span class="meta-item">
                                <i class="fas fa-list"></i>
                                ${menu.options_count || 0} roles
                            </span>
                        </div>
                    </div>
                    <div class="role-menu-actions">
                        <button class="action-btn-small" onclick="dashboard.sendRoleMenu(${menu.id})" style="background: #28a745; border-color: #28a745;">
                            <i class="fas fa-paper-plane"></i>
                            Send
                        </button>
                        <button class="action-btn-small" onclick="dashboard.editRoleMenu(${menu.id})">
                            <i class="fas fa-edit"></i>
                            Edit
                        </button>
                        <button class="action-btn-small" onclick="dashboard.deleteRoleMenu(${menu.id})" style="background: #dc3545; border-color: #dc3545;">
                            <i class="fas fa-trash"></i>
                            Delete
                        </button>
                    </div>
                </div>
            </div>
        `;
        }).join('');
        console.log('✅ Role menus HTML updated');
    }

    async createRoleMenu() {
        // Show create role menu modal
        this.showRoleMenuModal();
    }

    async editRoleMenu(menuId) {
        console.log(`✏️ Editing role menu with ID: ${menuId}`);
        try {
            console.log(`📡 Fetching role menu data for ID: ${menuId}`);
            const response = await this.apiCall(`/guild/${this.currentGuild}/role-menus/${menuId}`);
            console.log(`✅ Received role menu data:`, response.menu);
            this.showRoleMenuModal(response.menu);
        } catch (error) {
            console.error('❌ Failed to load role menu:', error);
            this.showError('Failed to load role menu for editing.');
        }
    }

    async sendRoleMenu(menuId) {
        console.log(`📤 Attempting to send role menu with ID: ${menuId}`);
        
        try {
            console.log(`🔄 Making API call to send menu ${menuId}`);
            await this.apiCall(`/guild/${this.currentGuild}/role-menus/${menuId}/send`, 'POST');
            console.log(`✅ Send API call successful for menu ${menuId}`);
            this.showSuccess('Role menu sent to Discord channel successfully!');
        } catch (error) {
            console.error('❌ Failed to send role menu:', error);
            this.showError('Failed to send role menu. Please try again.');
        }
    }

    async deleteRoleMenu(menuId) {
        console.log(`🗑️ Attempting to delete role menu with ID: ${menuId}`);
        if (!confirm('Are you sure you want to delete this role menu? This action cannot be undone.')) {
            console.log('❌ User cancelled deletion');
            return;
        }

        try {
            console.log(`🔄 Making API call to delete menu ${menuId}`);
            await this.apiCall(`/guild/${this.currentGuild}/role-menus/${menuId}`, 'DELETE');
            console.log(`✅ Delete API call successful for menu ${menuId}`);
            this.showSuccess('Role menu deleted successfully!');
            console.log(`🔄 Refreshing role menus list...`);
            await this.loadRoleMenus(); // Add await here
            console.log(`✅ Role menus list refreshed`);
        } catch (error) {
            console.error('❌ Failed to delete role menu:', error);
            this.showError('Failed to delete role menu. Please try again.');
        }
    }

    showRoleMenuModal(menu = null) {
        const isEdit = menu !== null;
        console.log(`🪟 Showing role menu modal - isEdit: ${isEdit}`);
        if (isEdit) {
            console.log(`📝 Edit mode - menu data:`, menu);
            console.log(`📝 Channel ID to pre-select: ${menu.channel_id}`);
        }
        
        // Create modal HTML
        const modalHtml = `
            <div class="modal-overlay" id="roleMenuModal">
                <div class="modal-content large-modal">
                    <div class="modal-header">
                        <h3>${isEdit ? 'Edit Role Menu' : 'Create Role Menu'}</h3>
                        <button class="modal-close" onclick="dashboard.closeRoleMenuModal()">
                            <i class="fas fa-times"></i>
                        </button>
                    </div>
                    <div class="modal-body">
                        <form id="roleMenuForm">
                            <div class="form-grid">
                                <div class="form-group">
                                    <label class="form-label">Menu Title</label>
                                    <input type="text" id="menuTitle" class="form-input" 
                                           value="${isEdit ? this.escapeHtml(menu.title) : ''}" 
                                           placeholder="Select Your Role" required maxlength="256">
                                </div>
                                
                                <div class="form-group">
                                    <label class="form-label">Channel</label>
                                    <select id="menuChannel" class="form-select" required>
                                        <option value="">Select a channel...</option>
                                    </select>
                                </div>
                                
                                <div class="form-group full-width">
                                    <label class="form-label">Description</label>
                                    <textarea id="menuDescription" class="form-textarea" rows="3" 
                                              placeholder="Choose a role from the dropdown below">${isEdit ? this.escapeHtml(menu.description || '') : ''}</textarea>
                                </div>
                                
                                <div class="form-group">
                                    <label class="form-label">Color</label>
                                    <input type="text" id="menuColor" class="form-input" 
                                           value="${isEdit ? menu.color : '#5865F2'}" 
                                           placeholder="#5865F2" pattern="^#[0-9A-Fa-f]{6}$">
                                </div>
                                
                                <div class="form-group">
                                    <label class="form-label">Placeholder Text</label>
                                    <input type="text" id="menuPlaceholder" class="form-input" 
                                           value="${isEdit ? this.escapeHtml(menu.placeholder || '') : 'Select a role...'}" 
                                           placeholder="Select a role..." maxlength="150">
                                </div>
                                
                                <div class="form-group">
                                    <label class="form-label">Selection Mode</label>
                                    <select id="selectionMode" class="form-select" onchange="dashboard.updateSelectionValues()">
                                        <option value="single" ${isEdit && menu.max_values === 1 ? 'selected' : ''}>Single Selection (1 role)</option>
                                        <option value="multiple" ${isEdit && menu.max_values > 1 ? 'selected' : !isEdit ? 'selected' : ''}>Multiple Selection</option>
                                    </select>
                                </div>
                                
                                <div class="form-group" id="maxValuesGroup" style="${isEdit && menu.max_values === 1 ? 'display: none;' : ''}">
                                    <label class="form-label">Maximum Selections</label>
                                    <input type="number" id="maxValues" class="form-input" 
                                           value="${isEdit ? menu.max_values : 5}" 
                                           min="1" max="25" placeholder="5">
                                    <small class="form-help">Maximum number of roles a user can select (1-25)</small>
                                </div>
                            </div>
                            
                            <div class="form-section">
                                <div class="section-header">
                                    <h4>Role Options</h4>
                                    <button type="button" class="btn-secondary" onclick="dashboard.addRoleOption()">
                                        <i class="fas fa-plus"></i>
                                        Add Role
                                    </button>
                                </div>
                                <div id="roleOptionsList" class="role-options-list">
                                    <!-- Role options will be added here -->
                                </div>
                            </div>
                        </form>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn-secondary" onclick="dashboard.closeRoleMenuModal()">Cancel</button>
                        <button type="button" class="btn-primary" onclick="dashboard.saveRoleMenu(${isEdit ? menu.id : 'null'})">
                            ${isEdit ? 'Update Menu' : 'Create Menu'}
                        </button>
                    </div>
                </div>
            </div>
        `;
        
        // Add modal to page
        document.body.insertAdjacentHTML('beforeend', modalHtml);
        
        // Small delay to ensure DOM is ready, then load channels and roles
        setTimeout(async () => {
            console.log(`⏱️ Starting async loading of channels and roles`);
            console.log(`📍 Channel ID to select: ${isEdit ? menu.channel_id : null}`);
            await this.loadChannelsForModal(isEdit ? menu.channel_id : null);
            await this.loadRolesForModal();
            
            // After loading channels, ensure the correct channel is selected
            if (isEdit && menu.channel_id) {
                console.log(`🔄 Double-checking channel selection...`);
                const channelSelect = document.getElementById('menuChannel');
                if (channelSelect) {
                    console.log(`📋 Channel select current value: "${channelSelect.value}"`);
                    console.log(`🎯 Setting channel select value to: "${menu.channel_id}"`);
                    channelSelect.value = String(menu.channel_id);
                    console.log(`✅ Channel select value after setting: "${channelSelect.value}"`);
                } else {
                    console.error(`❌ Channel select element not found!`);
                }
            }
        }, 100);
        
        // Load existing options if editing
        if (isEdit && menu.options) {
            menu.options.forEach(option => {
                this.addRoleOption(option);
            });
        } else {
            // Add one empty option by default
            this.addRoleOption();
        }
    }

    updateSelectionValues() {
        const selectionMode = document.getElementById('selectionMode').value;
        const maxValuesGroup = document.getElementById('maxValuesGroup');
        const maxValuesInput = document.getElementById('maxValues');
        
        if (selectionMode === 'single') {
            maxValuesGroup.style.display = 'none';
            maxValuesInput.value = 1;
        } else {
            maxValuesGroup.style.display = 'block';
            if (maxValuesInput.value == 1) {
                maxValuesInput.value = 5; // Default to 5 for multiple selection
            }
        }
    }

    closeRoleMenuModal() {
        const modal = document.getElementById('roleMenuModal');
        if (modal) {
            modal.remove();
        }
    }

    async loadChannelsForModal(selectedChannelId = null) {
        console.log(`📡 Loading channels for modal with selectedChannelId: ${selectedChannelId}`);
        const channelSelect = document.getElementById('menuChannel');
        if (!channelSelect) {
            console.error('❌ menuChannel select element not found');
            return;
        }
        
        console.log('🔍 Current channels available:', this.channels?.length || 0);
        console.log('🎯 Selected channel ID to match:', selectedChannelId);
        
        // Clear existing options
        channelSelect.innerHTML = '<option value="">Select a channel...</option>';
        
        // Use the same channels that are already loaded (like in welcome section)
        if (this.channels && this.channels.length > 0) {
            console.log(`📝 Adding ${this.channels.length} channels to role menu modal`);
            this.channels.forEach(channel => {
                const option = document.createElement('option');
                option.value = channel.id;
                option.textContent = `#${channel.name}`;
                
                console.log(`🔍 Comparing channel "${channel.name}" (${channel.id}) with selected (${selectedChannelId})`);
                console.log(`   - channel.id type: ${typeof channel.id}, value: "${channel.id}"`);
                console.log(`   - selectedChannelId type: ${typeof selectedChannelId}, value: "${selectedChannelId}"`);
                
                if (selectedChannelId && String(channel.id) === String(selectedChannelId)) {
                    option.selected = true;
                    console.log(`✅ Pre-selected channel: #${channel.name} (${channel.id})`);
                }
                channelSelect.appendChild(option);
            });
            console.log(`✅ Added all channels to select`);
        } else {
            // If channels aren't loaded yet, try to load them
            console.warn('⚠️ No channels available for role menu. Attempting to reload...');
            try {
                await this.loadGuildChannels();
                console.log('🔄 Reloaded channels:', this.channels?.length || 0);
                if (this.channels && this.channels.length > 0) {
                    this.channels.forEach(channel => {
                        const option = document.createElement('option');
                        option.value = channel.id;
                        option.textContent = `#${channel.name}`;
                        if (selectedChannelId && String(channel.id) === String(selectedChannelId)) {
                            option.selected = true;
                            console.log(`✅ Pre-selected channel after reload: #${channel.name} (${channel.id})`);
                        }
                        channelSelect.appendChild(option);
                    });
                    console.log(`✅ Added ${this.channels.length} channels after reload`);
                }
            } catch (error) {
                console.error('❌ Failed to load channels for role menu:', error);
            }
        }
    }

    async loadRolesForModal() {
        // This will be called when role options are added
        // The actual role loading happens in loadRolesForOption() for each individual role select
        console.log('loadRolesForModal called - roles will be loaded per option');
    }

    addRoleOption(optionData = null) {
        const optionsList = document.getElementById('roleOptionsList');
        const optionId = Date.now() + Math.random();
        
        const optionHtml = `
            <div class="role-option-item" data-option-id="${optionId}">
                <div class="role-option-grid">
                    <div class="form-group">
                        <label class="form-label">Role</label>
                        <select class="role-select" required>
                            <option value="">Select a role...</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label class="form-label">Label</label>
                        <input type="text" class="option-label" placeholder="Member Role" 
                               value="${optionData ? this.escapeHtml(optionData.label) : ''}" maxlength="80" required>
                    </div>
                    <div class="form-group">
                        <label class="form-label">Description</label>
                        <input type="text" class="option-description" placeholder="Access to member-only channels" 
                               value="${optionData ? this.escapeHtml(optionData.description || '') : ''}" maxlength="100">
                    </div>
                    <div class="form-group">
                        <label class="form-label">Emoji (optional)</label>
                        <input type="text" class="option-emoji" placeholder="🎭" 
                               value="${optionData ? this.escapeHtml(optionData.emoji || '') : ''}" maxlength="10">
                    </div>
                </div>
                <button type="button" class="remove-option-btn" onclick="dashboard.removeRoleOption('${optionId}')">
                    <i class="fas fa-trash"></i>
                </button>
            </div>
        `;
        
        optionsList.insertAdjacentHTML('beforeend', optionHtml);
        
        // Load roles for the new option
        this.loadRolesForOption(optionId, optionData?.role_id);
    }

    async loadRolesForOption(optionId, selectedRoleId = null) {
        console.log(`🎭 Loading roles for option ${optionId} with selectedRoleId: ${selectedRoleId}`);
        const optionElement = document.querySelector(`[data-option-id="${optionId}"]`);
        const roleSelect = optionElement.querySelector('.role-select');
        
        if (!this.currentGuild) {
            console.log('❌ No current guild for role loading');
            return;
        }
        
        try {
            console.log(`📡 Fetching roles for guild ${this.currentGuild}`);
            const response = await this.apiCall(`/guild/${this.currentGuild}/roles`);
            const roles = response.roles || [];
            console.log(`✅ Received ${roles.length} roles`);
            
            roleSelect.innerHTML = '<option value="">Select a role...</option>';
            
            roles.forEach(role => {
                if (role.name !== '@everyone') {  // Skip @everyone role
                    const option = document.createElement('option');
                    option.value = role.id;
                    option.textContent = role.name;
                    
                    console.log(`🔍 Comparing role "${role.name}" (${role.id}) with selected (${selectedRoleId})`);
                    console.log(`   - role.id type: ${typeof role.id}, value: "${role.id}"`);
                    console.log(`   - selectedRoleId type: ${typeof selectedRoleId}, value: "${selectedRoleId}"`);
                    
                    if (selectedRoleId && String(role.id) === String(selectedRoleId)) {
                        option.selected = true;
                        console.log(`✅ Pre-selected role: ${role.name} (${role.id})`);
                    }
                    roleSelect.appendChild(option);
                }
            });
            console.log(`✅ Added roles to option ${optionId}`);
        } catch (error) {
            console.error(`❌ Failed to load roles for option ${optionId}:`, error);
        }
    }

    removeRoleOption(optionId) {
        const optionElement = document.querySelector(`[data-option-id="${optionId}"]`);
        if (optionElement) {
            optionElement.remove();
        }
    }

    async saveRoleMenu(menuId) {
        const form = document.getElementById('roleMenuForm');
        const formData = new FormData(form);
        
        // Collect basic menu data
        const menuData = {
            title: document.getElementById('menuTitle').value.trim(),
            channel_id: document.getElementById('menuChannel').value,
            description: document.getElementById('menuDescription').value.trim(),
            color: document.getElementById('menuColor').value.trim(),
            placeholder: document.getElementById('menuPlaceholder').value.trim(),
            min_values: 0, // Always allow no selection
            max_values: parseInt(document.getElementById('maxValues').value) || 1
        };
        
        // Validate required fields
        if (!menuData.title || !menuData.channel_id) {
            this.showError('Please fill in all required fields.');
            return;
        }
        
        // Collect role options
        const options = [];
        const optionElements = document.querySelectorAll('.role-option-item');
        
        for (let i = 0; i < optionElements.length; i++) {
            const element = optionElements[i];
            const roleId = element.querySelector('.role-select').value;
            const label = element.querySelector('.option-label').value.trim();
            const description = element.querySelector('.option-description').value.trim();
            const emoji = element.querySelector('.option-emoji').value.trim();
            
            if (!roleId || !label) {
                this.showError('Please fill in role and label for all options.');
                return;
            }
            
            options.push({
                role_id: roleId,
                label: label,
                description: description,
                emoji: emoji,
                position: i
            });
        }
        
        if (options.length === 0) {
            this.showError('Please add at least one role option.');
            return;
        }
        
        try {
            const url = menuId ? `/guild/${this.currentGuild}/role-menus/${menuId}` : `/guild/${this.currentGuild}/role-menus`;
            const method = menuId ? 'PUT' : 'POST';
            
            const response = await this.apiCall(url, method, {
                menu: menuData,
                options: options
            });
            
            this.showSuccess(menuId ? 'Role menu updated successfully!' : 'Role menu created successfully!');
            this.closeRoleMenuModal();
            
            console.log('🔄 Reloading role menus after successful creation/update');
            await this.loadRoleMenus(); // Make it await for proper sequencing
            
        } catch (error) {
            console.error('Failed to save role menu:', error);
            this.showError('Failed to save role menu. Please try again.');
        }
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    async loadGuildMembers() {
        // Return cached data if available and not stale
        if (this.members && this.dataLoaded?.members) {
            console.log('✅ Using cached guild members');
            return;
        }
        
        if (!this.currentGuild) return;

        try {
            console.log('🔄 Loading guild members...');
            const response = await this.apiCall(`/guild/${this.currentGuild}/members`);
            this.members = response.members || []; // Store members for later use
            
            if (this.dataLoaded) this.dataLoaded.members = true;
            
            console.log('Loaded guild members:', this.members.length);
            if (this.members.length > 0) {
                console.log('Sample member:', this.members[0]);
                console.log('All member IDs:', this.members.map(m => ({id: m.id, name: m.display_name || m.username})));
            }
            
            const memberSelect = document.getElementById('memberSelect');
            if (memberSelect) {
                memberSelect.innerHTML = `<option value="">${this.getString('moderation.choose_member')}</option>`;
                
                if (this.members.length > 0) {
                    this.members.forEach(member => {
                        const option = document.createElement('option');
                        option.value = member.id;
                        option.textContent = member.display_name || member.username;
                        memberSelect.appendChild(option);
                    });
                } else {
                    const option = document.createElement('option');
                    option.value = '';
                    option.textContent = this.getString('moderation.no_members') || 'No members available - Enable GUILD_MEMBERS intent in Discord Developer Portal';
                    option.disabled = true;
                    memberSelect.appendChild(option);
                }
            }
            
        } catch (error) {
            console.error('Failed to load guild members:', error);
            this.members = []; // Set empty array on error
            
            if (this.dataLoaded) this.dataLoaded.members = false; // Mark as failed to load
            
            const memberSelect = document.getElementById('memberSelect');
            if (memberSelect) {
                memberSelect.innerHTML = `<option value="">${this.getString('errors.load_error')}</option>`;
            }
        }
    }

    // Refresh displays that show user names after members are loaded
    async refreshUserDisplays() {
        try {
            // Refresh top users if stats are already loaded
            if (this.currentGuild) {
                const statsResponse = await this.apiCall(`/guild/${this.currentGuild}/stats`);
                const stats = statsResponse;
                
                const topUsersTable = document.getElementById('topUsersTable');
                if (topUsersTable && stats.top_users && stats.top_users.length > 0) {
                    topUsersTable.innerHTML = '';
                    for (const [index, user] of stats.top_users.entries()) {
                        const row = document.createElement('tr');
                        const displayName = await this.getUserDisplayNameAsync(user.user_id);
                        row.innerHTML = `
                            <td><span class="badge bg-primary">#${index + 1}</span></td>
                            <td>${displayName}</td>
                            <td><span class="badge bg-success">Level ${user.level}</span></td>
                            <td>${user.xp?.toLocaleString() || '0'} XP</td>
                        `;
                        topUsersTable.appendChild(row);
                    }
                }
                
                // Refresh moderation history too
                const historyResponse = await this.apiCall(`/guild/${this.currentGuild}/moderation/history`);
                const history = historyResponse.history || [];
                
                const historyTable = document.getElementById('moderationHistoryTable');
                if (historyTable && history.length > 0) {
                    historyTable.innerHTML = '';
                    for (const action of history) {
                        const row = document.createElement('tr');
                        const actionBadge = action.action_type === 'warning' ? 'bg-warning' : 'bg-danger';
                        const displayName = await this.getUserDisplayNameAsync(action.user_id);
                        row.innerHTML = `
                            <td>${displayName}</td>
                            <td><span class="badge ${actionBadge}">${action.action_type}</span></td>
                            <td>${new Date(action.created_at).toLocaleDateString()}</td>
                        `;
                        historyTable.appendChild(row);
                    }
                }
            }
        } catch (error) {
            console.error('Failed to refresh user displays:', error);
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
                historyTable.innerHTML = '';
                for (const action of history) {
                    const row = document.createElement('tr');
                    const actionBadge = action.action_type === 'warning' ? 'bg-warning' : 'bg-danger';
                    const displayName = await this.getUserDisplayNameAsync(action.user_id);
                    row.innerHTML = `
                        <td>${displayName}</td>
                        <td><span class="badge ${actionBadge}">${action.action_type}</span></td>
                        <td>${new Date(action.created_at).toLocaleDateString()}</td>
                    `;
                    historyTable.appendChild(row);
                }
            } else {
                historyTable.innerHTML = `<tr><td colspan="3" class="text-center text-muted">${this.getString('overview.no_history')}</td></tr>`;
            }
            
        } catch (error) {
            console.error('Failed to load moderation history:', error);
            const historyTable = document.getElementById('moderationHistoryTable');
            historyTable.innerHTML = `<tr><td colspan="3" class="text-center text-muted">${this.getString('errors.load_error')}</td></tr>`;
        }
    }

    async loadWelcomeConfig() {
        if (!this.currentGuild) return;

        try {
            const config = await this.apiCall(`/guild/${this.currentGuild}/welcome`);
            
            document.getElementById('welcomeEnabled').checked = config.welcome_enabled || false;
            document.getElementById('welcomeChannel').value = config.welcome_channel || '';
            document.getElementById('welcomeTitle').value = config.welcome_title || '👋 New member!';
            document.getElementById('welcomeMessage').value = config.welcome_message || 'Welcome {user} to {server}!';
            
            // Handle welcome fields
            const welcomeFieldsToggle = document.getElementById('welcomeFields');
            const welcomeFieldsContainer = document.getElementById('welcomeFieldsContainer');
            const welcomeFieldsList = document.getElementById('welcomeFieldsList');
            
            if (config.welcome_fields && config.welcome_fields.length > 0) {
                welcomeFieldsToggle.checked = true;
                welcomeFieldsContainer.style.display = 'block';
                
                // Clear existing fields
                welcomeFieldsList.innerHTML = '';
                
                // Add fields from config
                config.welcome_fields.forEach(field => {
                    const fieldItem = this.createFieldItem(field.name, field.value, field.inline, welcomeFieldsList);
                    welcomeFieldsList.appendChild(fieldItem);
                });
                
                this.updateFieldMoveButtons(welcomeFieldsList);
            } else {
                welcomeFieldsToggle.checked = false;
                welcomeFieldsContainer.style.display = 'none';
                welcomeFieldsList.innerHTML = '';
            }
            
            document.getElementById('goodbyeEnabled').checked = config.goodbye_enabled || false;
            document.getElementById('goodbyeChannel').value = config.goodbye_channel || '';
            document.getElementById('goodbyeTitle').value = config.goodbye_title || '👋 Departure';
            document.getElementById('goodbyeMessage').value = config.goodbye_message || 'Goodbye {user}, thanks for being part of {server}!';
            
            // Handle goodbye fields
            const goodbyeFieldsToggle = document.getElementById('goodbyeFields');
            const goodbyeFieldsContainer = document.getElementById('goodbyeFieldsContainer');
            const goodbyeFieldsList = document.getElementById('goodbyeFieldsList');
            
            if (config.goodbye_fields && config.goodbye_fields.length > 0) {
                goodbyeFieldsToggle.checked = true;
                goodbyeFieldsContainer.style.display = 'block';
                
                // Clear existing fields
                goodbyeFieldsList.innerHTML = '';
                
                // Add fields from config
                config.goodbye_fields.forEach(field => {
                    const fieldItem = this.createFieldItem(field.name, field.value, field.inline, goodbyeFieldsList);
                    goodbyeFieldsList.appendChild(fieldItem);
                });
                
                this.updateFieldMoveButtons(goodbyeFieldsList);
            } else {
                goodbyeFieldsToggle.checked = false;
                goodbyeFieldsContainer.style.display = 'none';
                goodbyeFieldsList.innerHTML = '';
            }
            
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
            this.showError(this.getString('messages.please_select_server') || 'Please select a server first.');
            return;
        }

        const memberId = document.getElementById('memberSelect').value;
        const action = document.getElementById('moderationAction').value;
        const reason = document.getElementById('moderationReason').value;
        const channelId = document.getElementById('moderationChannel').value;

        if (!memberId || !action) {
            this.showError(this.getString('moderation.select_member_action') || 'Please select a member and action.');
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
            this.showSuccess(this.getString('moderation.action_success') || `${action.charAt(0).toUpperCase() + action.slice(1)} executed successfully!`);
            
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
            this.showError(this.getString('moderation.action_error') || 'Failed to execute moderation action. Please try again.');
        }
    }

    async saveWelcomeSettings(event) {
        event.preventDefault();
        
        if (!this.currentGuild) {
            this.showError(this.getString('messages.please_select_server') || 'Please select a server first.');
            return;
        }

        try {
            // Parse custom fields if enabled
            let welcomeFields = null;
            let goodbyeFields = null;
            
            if (document.getElementById('welcomeFields').checked) {
                welcomeFields = this.collectWelcomeFields();
            }
            
            if (document.getElementById('goodbyeFields').checked) {
                goodbyeFields = this.collectGoodbyeFields();
            }

            const welcomeConfig = {
                welcome_enabled: document.getElementById('welcomeEnabled').checked,
                welcome_channel: document.getElementById('welcomeChannel').value || null,
                welcome_title: document.getElementById('welcomeTitle').value || '👋 New member!',
                welcome_message: document.getElementById('welcomeMessage').value || 'Welcome {user} to {server}!',
                welcome_fields: welcomeFields,
                goodbye_enabled: document.getElementById('goodbyeEnabled').checked,
                goodbye_channel: document.getElementById('goodbyeChannel').value || null,
                goodbye_title: document.getElementById('goodbyeTitle').value || '👋 Departure',
                goodbye_message: document.getElementById('goodbyeMessage').value || 'Goodbye {user}, thanks for being part of {server}!',
                goodbye_fields: goodbyeFields,
                auto_role_enabled: document.getElementById('autoRoleEnabled').checked,
                auto_role_ids: this.getSelectedAutoRoles()
            };

            await this.apiCall(`/guild/${this.currentGuild}/welcome`, 'PUT', welcomeConfig);
            this.showSuccess(this.getString('messages.welcome_settings_saved') || 'Welcome settings saved successfully!');
            
        } catch (error) {
            console.error('Failed to save welcome settings:', error);
            this.showError(this.getString('messages.save_error') || 'Failed to save welcome settings. Please try again.');
        }
    }

    collectWelcomeFields() {
        const fields = [];
        const fieldItems = document.querySelectorAll('#welcomeFieldsList .custom-field-item');
        fieldItems.forEach(item => {
            const name = item.querySelector('.field-name').value.trim();
            const value = item.querySelector('.field-value').value.trim();
            const inline = item.querySelector('.field-inline').checked;
            
            if (name && value) {
                fields.push({ name, value, inline });
            }
        });
        return fields.length > 0 ? fields : null;
    }

    collectGoodbyeFields() {
        const fields = [];
        const fieldItems = document.querySelectorAll('#goodbyeFieldsList .custom-field-item');
        fieldItems.forEach(item => {
            const name = item.querySelector('.field-name').value.trim();
            const value = item.querySelector('.field-value').value.trim();
            const inline = item.querySelector('.field-inline').checked;
            
            if (name && value) {
                fields.push({ name, value, inline });
            }
        });
        return fields.length > 0 ? fields : null;
    }

    createFieldItem(name = '', value = '', inline = false, container) {
        const fieldItem = document.createElement('div');
        fieldItem.className = 'custom-field-item';
        fieldItem.innerHTML = `
            <div class="field-input-group">
                <label>Field Name</label>
                <input type="text" class="field-input form-control field-name" placeholder="e.g., Server Rules" value="${name}">
            </div>
            <div class="field-input-group">
                <label>Field Value</label>
                <textarea class="field-input form-control field-value" placeholder="e.g., Please read #rules" rows="3">${value}</textarea>
            </div>
            <div class="field-toggle-wrapper">
                <div class="toggle-label-text">Inline</div>
                <div class="field-toggle-switch">
                    <input type="checkbox" class="field-inline" ${inline ? 'checked' : ''}>
                    <span class="field-toggle-slider"></span>
                </div>
            </div>
            <div class="field-actions">
                <button type="button" class="field-move-btn field-up" title="Move Up">
                    <i class="fas fa-chevron-up"></i>
                </button>
                <button type="button" class="field-remove-btn" title="Remove Field">
                    <i class="fas fa-trash"></i>
                </button>
            </div>
        `;

        // Add event listeners
        fieldItem.querySelector('.field-remove-btn').addEventListener('click', () => {
            fieldItem.remove();
            this.updateFieldMoveButtons(container);
        });

        fieldItem.querySelector('.field-up').addEventListener('click', () => {
            const prev = fieldItem.previousElementSibling;
            if (prev) {
                container.insertBefore(fieldItem, prev);
                this.updateFieldMoveButtons(container);
            }
        });

        // Add toggle functionality
        const toggleSlider = fieldItem.querySelector('.field-toggle-slider');
        const toggleInput = fieldItem.querySelector('.field-inline');
        
        toggleSlider.addEventListener('click', () => {
            toggleInput.checked = !toggleInput.checked;
            toggleInput.dispatchEvent(new Event('change'));
        });

        return fieldItem;
    }

    updateFieldMoveButtons(container) {
        const items = container.querySelectorAll('.custom-field-item');
        items.forEach((item, index) => {
            const upBtn = item.querySelector('.field-up');
            upBtn.disabled = index === 0;
        });
    }

    async saveServerLogsSettings(event) {
        event.preventDefault();
        
        if (!this.currentGuild) {
            this.showError(this.getString('messages.please_select_server') || 'Please select a server first.');
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
            this.showSuccess(this.getString('messages.logs_settings_saved') || 'Server logs settings saved successfully!');
            
        } catch (error) {
            console.error('Failed to save server logs settings:', error);
            this.showError(this.getString('messages.save_error') || 'Failed to save server logs settings. Please try again.');
        }
    }

    async testWelcomeMessage() {
        if (!this.currentGuild) {
            this.showError(this.getString('messages.please_select_server') || 'Please select a server first.');
            return;
        }

        try {
            await this.apiCall(`/guild/${this.currentGuild}/welcome/test`, 'POST');
            this.showSuccess(this.getString('messages.test_success') || 'Test welcome message sent successfully!');
        } catch (error) {
            console.error('Failed to send test welcome message:', error);
            this.showError(this.getString('messages.test_error') || 'Failed to send test welcome message. Please try again.');
        }
    }

    async testServerLog() {
        if (!this.currentGuild) {
            this.showError(this.getString('messages.please_select_server') || 'Please select a server first.');
            return;
        }

        try {
            await this.apiCall(`/guild/${this.currentGuild}/logs/test`, 'POST');
            this.showSuccess(this.getString('messages.test_success') || 'Test server log sent successfully!');
        } catch (error) {
            console.error('Failed to send test server log:', error);
            this.showError(this.getString('messages.test_error') || 'Failed to send test server log. Please try again.');
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
        await this.loadGuildRoles();  // Add this to load roles for level roles dropdown
        this.populateXPSettings();
        
        // Mark as loaded
        if (this.dataLoaded) {
            this.dataLoaded.roles = true;
        }
    }

    async loadModerationData() {
        // Check if already loaded
        if (this.dataLoaded?.moderation) {
            console.log('✅ Moderation data already loaded');
            return;
        }
        
        console.log('🔄 Loading moderation data...');
        
        // Load in parallel for better performance
        await Promise.all([
            this.loadGuildMembers(),
            this.loadGuildChannels(),
            this.loadModerationHistory()
        ]);
        
        this.populateModerationSettings();
        
        // Mark as loaded
        if (this.dataLoaded) {
            this.dataLoaded.moderation = true;
            this.dataLoaded.members = true;
            this.dataLoaded.channels = true;
        }
    }

    async loadWelcomeSettings() {
        // Check if already loaded
        if (this.dataLoaded?.welcome) {
            console.log('✅ Welcome data already loaded');
            return;
        }
        
        console.log('🔄 Loading welcome data...');
        
        // Load in parallel for better performance
        await Promise.all([
            this.loadWelcomeConfig(),
            this.loadGuildChannels(),
            this.loadGuildRoles()
        ]);
        
        this.populateWelcomeSettings();
        
        // Mark as loaded
        if (this.dataLoaded) {
            this.dataLoaded.welcome = true;
            this.dataLoaded.channels = true;
            this.dataLoaded.roles = true;
        }
    }

    async loadLogsSettings() {
        // Check if already loaded
        if (this.dataLoaded?.logs) {
            console.log('✅ Logs data already loaded');
            return;
        }
        
        console.log('🔄 Loading logs data...');
        
        // Load in parallel for better performance
        await Promise.all([
            this.loadServerLogsConfig(),
            this.loadGuildChannels()
        ]);
        
        this.populateLogsSettings();
        
        // Mark as loaded
        if (this.dataLoaded) {
            this.dataLoaded.logs = true;
            this.dataLoaded.channels = true;
        }
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

    getSelectedAutoRoles() {
        const selectedRoles = [];
        const roleElements = document.querySelectorAll('#selectedRoles .role-tag');
        roleElements.forEach(element => {
            const roleId = element.dataset.roleId;
            if (roleId) {
                selectedRoles.push(roleId);
            }
        });
        return selectedRoles;
    }

    initAutoRoleSelector() {
        const autoRoleEnabled = document.getElementById('autoRoleEnabled');
        const autoRoleContainer = document.getElementById('autoRoleContainer');
        const roleSelect = document.getElementById('roleSelect');
        const selectedRoles = document.getElementById('selectedRoles');

        // Toggle auto-role container visibility
        autoRoleEnabled.addEventListener('change', () => {
            autoRoleContainer.style.display = autoRoleEnabled.checked ? 'block' : 'none';
        });

        // Handle role selection
        roleSelect.addEventListener('change', (e) => {
            const selectedOptions = Array.from(e.target.selectedOptions);
            selectedOptions.forEach(option => {
                if (option.value && !this.isRoleAlreadySelected(option.value)) {
                    this.addSelectedRole(option.value, option.textContent);
                }
            });
            // Clear selections after adding
            e.target.selectedIndex = -1;
        });
    }

    isRoleAlreadySelected(roleId) {
        return document.querySelector(`#selectedRoles .role-tag[data-role-id="${roleId}"]`) !== null;
    }

    addSelectedRole(roleId, roleName) {
        const selectedRoles = document.getElementById('selectedRoles');
        const roleTag = document.createElement('div');
        roleTag.className = 'role-tag new-role';
        roleTag.dataset.roleId = roleId;
        roleTag.innerHTML = `
            <span class="role-name">${this.escapeHtml(roleName)}</span>
            <button type="button" class="remove-role" onclick="dashboard.removeSelectedRole('${roleId}')">
                <i class="fas fa-times"></i>
            </button>
        `;
        selectedRoles.appendChild(roleTag);
    }

    removeSelectedRole(roleId) {
        const roleTag = document.querySelector(`#selectedRoles .role-tag[data-role-id="${roleId}"]`);
        if (roleTag) {
            roleTag.remove();
        }
    }

    populateAutoRoleSettings(config) {
        const autoRoleEnabled = document.getElementById('autoRoleEnabled');
        const autoRoleContainer = document.getElementById('autoRoleContainer');
        const selectedRoles = document.getElementById('selectedRoles');
        
        // Set auto-role enabled state
        autoRoleEnabled.checked = config.auto_role_enabled || false;
        autoRoleContainer.style.display = autoRoleEnabled.checked ? 'block' : 'none';
        
        // Clear existing selected roles
        selectedRoles.innerHTML = '';
        
        // Populate selected roles
        if (config.auto_role_ids && Array.isArray(config.auto_role_ids)) {
            config.auto_role_ids.forEach(roleId => {
                // Find role name from guild roles
                const role = this.findRoleInGuild(roleId);
                if (role) {
                    this.addSelectedRole(roleId, role.name);
                }
            });
        }
    }

    findRoleInGuild(roleId) {
        if (this.roles && Array.isArray(this.roles)) {
            return this.roles.find(role => role.id === roleId);
        }
        return { name: `Role ${roleId}` }; // Fallback
    }

    async loadWelcomeConfig() {
        if (!this.currentGuild) return;

        try {
            console.log('Loading welcome config for guild:', this.currentGuild);
            this.welcomeConfig = await this.apiCall(`/guild/${this.currentGuild}/welcome`);
            console.log('Loaded welcome config:', this.welcomeConfig);
        } catch (error) {
            console.error('Failed to load welcome config:', error);
            this.welcomeConfig = {};
        }
    }

    populateWelcomeSettings() {
        // Populate welcome settings form
        console.log('Populating welcome settings...');
        
        if (!this.welcomeConfig) {
            console.warn('No welcome config loaded');
            return;
        }

        // Populate basic welcome settings
        const welcomeEnabled = document.getElementById('welcomeEnabled');
        const welcomeChannel = document.getElementById('welcomeChannel');
        const welcomeTitle = document.getElementById('welcomeTitle');
        const welcomeMessage = document.getElementById('welcomeMessage');

        if (welcomeEnabled) welcomeEnabled.checked = this.welcomeConfig.welcome_enabled || false;
        if (welcomeChannel) welcomeChannel.value = this.welcomeConfig.welcome_channel || '';
        if (welcomeTitle) welcomeTitle.value = this.welcomeConfig.welcome_title || '👋 New member!';
        if (welcomeMessage) welcomeMessage.value = this.welcomeConfig.welcome_message || 'Welcome {user} to {server}!';

        // Populate goodbye settings
        const goodbyeEnabled = document.getElementById('goodbyeEnabled');
        const goodbyeChannel = document.getElementById('goodbyeChannel');
        const goodbyeTitle = document.getElementById('goodbyeTitle');
        const goodbyeMessage = document.getElementById('goodbyeMessage');

        if (goodbyeEnabled) goodbyeEnabled.checked = this.welcomeConfig.goodbye_enabled || false;
        if (goodbyeChannel) goodbyeChannel.value = this.welcomeConfig.goodbye_channel || '';
        if (goodbyeTitle) goodbyeTitle.value = this.welcomeConfig.goodbye_title || '👋 Departure';
        if (goodbyeMessage) goodbyeMessage.value = this.welcomeConfig.goodbye_message || 'Goodbye {user}, thanks for being part of {server}!';

        // Populate auto-role settings
        this.populateAutoRoleSettings(this.welcomeConfig);
        
        // Initialize auto-role selector
        this.initAutoRoleSelector();
    }

    // Ticket System Methods
    async loadTicketSettings() {
        // Check if already loaded
        if (this.dataLoaded?.tickets) {
            console.log('✅ Ticket data already loaded');
            return;
        }
        
        console.log('🔄 Loading ticket data...');
        
        // Show loading state
        const ticketTab = document.getElementById('ticket-system');
        if (ticketTab) {
            const loadingHTML = `
                <div class="loading-state" style="text-align: center; padding: 2rem;">
                    <i class="fas fa-spinner fa-spin fa-2x" style="color: #5865F2;"></i>
                    <p style="margin-top: 1rem; color: #666;">Loading ticket system...</p>
                </div>
            `;
            ticketTab.innerHTML = loadingHTML;
        }

        try {
            // Load all data in parallel instead of sequentially
            const [ticketConfig, channels, roles, categories] = await Promise.all([
                this.loadTicketConfig(),
                this.loadGuildChannels(),
                this.loadGuildRoles(),
                this.loadGuildCategories()
            ]);
            
            this.populateTicketSettings();
            
            // Mark as loaded
            if (this.dataLoaded) {
                this.dataLoaded.tickets = true;
                this.dataLoaded.channels = true;
                this.dataLoaded.roles = true;
                this.dataLoaded.categories = true;
            }
            
        } catch (error) {
            console.error('Failed to load ticket settings:', error);
            if (ticketTab) {
                ticketTab.innerHTML = `
                    <div class="error-state" style="text-align: center; padding: 2rem;">
                        <i class="fas fa-exclamation-triangle fa-2x" style="color: #dc3545;"></i>
                        <p style="margin-top: 1rem; color: #dc3545;">Failed to load ticket system</p>
                        <button onclick="dashboard.loadTicketSettings()" class="btn btn-primary" style="margin-top: 1rem;">
                            Retry
                        </button>
                    </div>
                `;
            }
        }
    }

    async loadTicketConfig() {
        if (!this.currentGuild) return;

        try {
            console.log('Loading ticket config for guild:', this.currentGuild);
            this.ticketConfig = await this.apiCall(`/guild/${this.currentGuild}/tickets`);
            console.log('Loaded ticket config:', this.ticketConfig);
        } catch (error) {
            console.error('Failed to load ticket config:', error);
            this.ticketConfig = { enabled: false, panels: [] };
        }
    }

    populateTicketSettings() {
        console.log('Populating ticket settings...');
        
        if (!this.ticketConfig) {
            console.warn('No ticket config loaded');
            return;
        }

        // Set system enabled state
        const ticketSystemEnabled = document.getElementById('ticketSystemEnabled');
        const ticketPanelsSection = document.getElementById('ticketPanelsSection');
        
        if (ticketSystemEnabled) {
            ticketSystemEnabled.checked = this.ticketConfig.enabled || false;
            if (ticketPanelsSection) {
                ticketPanelsSection.style.display = this.ticketConfig.enabled ? 'block' : 'none';
            }
        }

        // Populate panels
        this.populateTicketPanels();
        
        // Initialize ticket system toggle
        this.initTicketSystemToggle();
    }

    populateTicketPanels() {
        const panelsList = document.getElementById('ticketPanelsList');
        const panelsEmpty = document.getElementById('ticketPanelsEmpty');
        
        if (!panelsList) return;

        panelsList.innerHTML = '';
        
        if (!this.ticketConfig.panels || this.ticketConfig.panels.length === 0) {
            if (panelsEmpty) panelsEmpty.style.display = 'block';
            return;
        }

        if (panelsEmpty) panelsEmpty.style.display = 'none';

        this.ticketConfig.panels.forEach(panel => {
            const panelElement = this.createTicketPanelElement(panel);
            panelsList.appendChild(panelElement);
        });
    }

    createTicketPanelElement(panel) {
        const template = document.getElementById('ticketPanelItemTemplate');
        const element = template.content.cloneNode(true);
        
        // Set panel data
        element.querySelector('.panel-name').textContent = panel.panel_name;
        element.querySelector('.panel-details').textContent = 
            `${panel.buttons ? panel.buttons.length : 0} buttons • ${panel.channel_id ? 'Deployed' : 'Not deployed'}`;
        
        // Set embed preview
        element.querySelector('.embed-title').textContent = panel.embed_title;
        element.querySelector('.embed-description').textContent = panel.embed_description;
        
        // Create button previews
        const buttonsContainer = element.querySelector('.embed-buttons');
        if (panel.buttons && panel.buttons.length > 0) {
            panel.buttons.forEach(button => {
                const buttonElement = document.createElement('span');
                buttonElement.className = `btn-preview btn-${button.button_style}`;
                buttonElement.textContent = `${button.button_emoji || ''} ${button.button_label}`.trim();
                buttonsContainer.appendChild(buttonElement);
            });
        }
        
        // Store panel data
        const panelItem = element.querySelector('.panel-item');
        panelItem.dataset.panelId = panel.id;
        panelItem.dataset.panelData = JSON.stringify(panel);
        
        return element;
    }

    initTicketSystemToggle() {
        const ticketSystemEnabled = document.getElementById('ticketSystemEnabled');
        const ticketPanelsSection = document.getElementById('ticketPanelsSection');
        
        if (ticketSystemEnabled && ticketPanelsSection) {
            ticketSystemEnabled.addEventListener('change', (e) => {
                ticketPanelsSection.style.display = e.target.checked ? 'block' : 'none';
                this.saveTicketSystemEnabled(e.target.checked);
            });
        }
    }

    async saveTicketSystemEnabled(enabled) {
        try {
            await this.apiCall(`/guild/${this.currentGuild}/tickets`, 'PUT', {
                enabled: enabled,
                panels: this.ticketConfig.panels || []
            });
            
            this.ticketConfig.enabled = enabled;
            this.showSuccess('Ticket system settings saved!');
        } catch (error) {
            console.error('Failed to save ticket system settings:', error);
            this.showError('Failed to save ticket system settings');
        }
    }

    createTicketPanel() {
        // Reset form
        document.getElementById('ticketPanelForm').reset();
        document.getElementById('ticketPanelId').value = '';
        document.getElementById('ticketPanelModalTitle').textContent = 'Create Ticket Panel';
        
        // Clear buttons list
        document.getElementById('ticketButtonsList').innerHTML = '';
        
        // Add first button by default
        this.addTicketButton();
        
        // Show modal
        const modal = new bootstrap.Modal(document.getElementById('ticketPanelModal'));
        modal.show();
    }

    editTicketPanel(button) {
        const panelItem = button.closest('.panel-item');
        const panelData = JSON.parse(panelItem.dataset.panelData);
        
        // Populate form
        document.getElementById('ticketPanelId').value = panelData.id;
        document.getElementById('ticketPanelName').value = panelData.panel_name;
        document.getElementById('ticketEmbedTitle').value = panelData.embed_title;
        document.getElementById('ticketEmbedDescription').value = panelData.embed_description;
        document.getElementById('ticketEmbedColor').value = panelData.embed_color;
        document.getElementById('ticketEmbedThumbnail').value = panelData.embed_thumbnail || '';
        document.getElementById('ticketEmbedFooter').value = panelData.embed_footer || '';
        
        document.getElementById('ticketPanelModalTitle').textContent = 'Edit Ticket Panel';
        
        // Clear and populate buttons
        const buttonsList = document.getElementById('ticketButtonsList');
        buttonsList.innerHTML = '';
        
        if (panelData.buttons && panelData.buttons.length > 0) {
            panelData.buttons.forEach(buttonData => {
                this.addTicketButton(buttonData);
            });
        } else {
            this.addTicketButton();
        }
        
        // Show modal
        const modal = new bootstrap.Modal(document.getElementById('ticketPanelModal'));
        modal.show();
    }

    addTicketButton(buttonData = null) {
        const template = document.getElementById('ticketButtonTemplate');
        const buttonElement = template.content.cloneNode(true);
        
        // Populate categories
        const categorySelect = buttonElement.querySelector('.button-category');
        if (this.categories && this.categories.length > 0) {
            this.categories.forEach(category => {
                const option = document.createElement('option');
                option.value = category.id;
                option.textContent = category.name;
                categorySelect.appendChild(option);
            });
        }
        
        // Populate roles for ping selection
        const rolesSelect = buttonElement.querySelector('.ping-roles-select');
        if (this.roles && this.roles.length > 0) {
            this.roles.forEach(role => {
                if (role.name !== '@everyone' && !role.managed) {
                    const option = document.createElement('option');
                    option.value = role.id;
                    option.textContent = role.name;
                    rolesSelect.appendChild(option);
                }
            });
        }
        
        // If editing, populate with existing data
        if (buttonData) {
            buttonElement.querySelector('.button-label').value = buttonData.button_label;
            buttonElement.querySelector('.button-emoji').value = buttonData.button_emoji || '';
            buttonElement.querySelector('.button-style').value = buttonData.button_style;
            buttonElement.querySelector('.button-category').value = buttonData.category_id || '';
            buttonElement.querySelector('.button-name-format').value = buttonData.ticket_name_format;
            buttonElement.querySelector('.button-initial-message').value = buttonData.initial_message || '';
            
            // Set selected roles
            if (buttonData.ping_roles && buttonData.ping_roles.length > 0) {
                const options = rolesSelect.options;
                for (let i = 0; i < options.length; i++) {
                    if (buttonData.ping_roles.includes(options[i].value)) {
                        options[i].selected = true;
                    }
                }
            }
        }
        
        document.getElementById('ticketButtonsList').appendChild(buttonElement);
    }

    removeTicketButton(button) {
        const buttonItem = button.closest('.button-config-item');
        buttonItem.remove();
    }

    async saveTicketPanel() {
        try {
            // Collect form data
            const panelId = document.getElementById('ticketPanelId').value;
            const panelData = {
                panel_name: document.getElementById('ticketPanelName').value,
                embed_title: document.getElementById('ticketEmbedTitle').value,
                embed_description: document.getElementById('ticketEmbedDescription').value,
                embed_color: document.getElementById('ticketEmbedColor').value,
                embed_thumbnail: document.getElementById('ticketEmbedThumbnail').value || null,
                embed_footer: document.getElementById('ticketEmbedFooter').value || null,
                buttons: []
            };
            
            // Collect button data
            const buttonElements = document.querySelectorAll('#ticketButtonsList .button-config-item');
            buttonElements.forEach((buttonElement, index) => {
                const pingRoles = Array.from(buttonElement.querySelector('.ping-roles-select').selectedOptions)
                    .map(option => option.value);
                
                panelData.buttons.push({
                    button_label: buttonElement.querySelector('.button-label').value,
                    button_emoji: buttonElement.querySelector('.button-emoji').value || null,
                    button_style: buttonElement.querySelector('.button-style').value,
                    category_id: buttonElement.querySelector('.button-category').value || null,
                    ticket_name_format: buttonElement.querySelector('.button-name-format').value,
                    ping_roles: pingRoles,
                    initial_message: buttonElement.querySelector('.button-initial-message').value || null,
                    button_order: index
                });
            });
            
            // Validate required fields
            if (!panelData.panel_name.trim()) {
                this.showError('Panel name is required');
                return;
            }
            
            if (panelData.buttons.length === 0) {
                this.showError('At least one button is required');
                return;
            }
            
            // Save panel
            let response;
            if (panelId) {
                // Update existing panel
                response = await this.apiCall(`/guild/${this.currentGuild}/tickets/panels/${panelId}`, 'PUT', panelData);
            } else {
                // Create new panel
                response = await this.apiCall(`/guild/${this.currentGuild}/tickets/panels`, 'POST', panelData);
            }
            
            this.showSuccess('Ticket panel saved successfully!');
            
            // Close modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('ticketPanelModal'));
            modal.hide();
            
            // Reload ticket settings
            await this.loadTicketConfig();
            this.populateTicketPanels();
            
        } catch (error) {
            console.error('Failed to save ticket panel:', error);
            this.showError('Failed to save ticket panel');
        }
    }

    async deleteTicketPanel(button) {
        const panelItem = button.closest('.panel-item');
        const panelData = JSON.parse(panelItem.dataset.panelData);
        
        if (!confirm(`Are you sure you want to delete the "${panelData.panel_name}" panel?`)) {
            return;
        }
        
        try {
            await this.apiCall(`/guild/${this.currentGuild}/tickets/panels/${panelData.id}`, 'DELETE');
            this.showSuccess('Ticket panel deleted successfully!');
            
            // Reload ticket settings
            await this.loadTicketConfig();
            this.populateTicketPanels();
            
        } catch (error) {
            console.error('Failed to delete ticket panel:', error);
            this.showError('Failed to delete ticket panel');
        }
    }

    deployTicketPanel(button) {
        const panelItem = button.closest('.panel-item');
        const panelData = JSON.parse(panelItem.dataset.panelData);
        
        // Store panel ID for deployment
        document.getElementById('deployPanelModal').dataset.panelId = panelData.id;
        
        // Populate channel selector
        const channelSelect = document.getElementById('deployChannelSelect');
        channelSelect.innerHTML = '<option value="">Select a channel...</option>';
        
        if (this.channels && this.channels.length > 0) {
            this.channels.forEach(channel => {
                const option = document.createElement('option');
                option.value = channel.id;
                option.textContent = `# ${channel.name}`;
                channelSelect.appendChild(option);
            });
        }
        
        // Show modal
        const modal = new bootstrap.Modal(document.getElementById('deployPanelModal'));
        modal.show();
    }

    async confirmDeployPanel() {
        const modal = document.getElementById('deployPanelModal');
        const panelId = modal.dataset.panelId;
        const channelId = document.getElementById('deployChannelSelect').value;
        
        if (!channelId) {
            this.showError('Please select a channel');
            return;
        }
        
        try {
            await this.apiCall(`/guild/${this.currentGuild}/tickets/panels/${panelId}/deploy`, 'POST', {
                channel_id: channelId
            });
            
            this.showSuccess('Ticket panel deployed successfully!');
            
            // Close modal
            const modalInstance = bootstrap.Modal.getInstance(modal);
            modalInstance.hide();
            
            // Reload ticket settings
            await this.loadTicketConfig();
            this.populateTicketPanels();
            
        } catch (error) {
            console.error('Failed to deploy ticket panel:', error);
            this.showError('Failed to deploy ticket panel');
        }
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    populateLogsSettings() {
        // Populate logs settings form
        console.log('Populating logs settings...');
    }

    // ===== EMBED CREATOR METHODS =====

    async initEmbedCreator() {
        console.log('🎨 Initializing embed creator...');
        
        // Initialize toggles
        this.initEmbedToggles();
        
        // Initialize color picker
        this.initColorPicker();
        
        // Initialize embed preview
        this.updateEmbedPreview();
        
        // Setup event listeners
        this.setupEmbedEventListeners();
        
        console.log('✅ Embed creator initialized');
    }

    initEmbedToggles() {
        // Ping role toggle
        const pingRoleToggle = document.getElementById('embedPingRole');
        const roleSelector = document.getElementById('embedRoleSelector');
        if (pingRoleToggle && roleSelector) {
            pingRoleToggle.addEventListener('change', (e) => {
                roleSelector.style.display = e.target.checked ? 'block' : 'none';
            });
        }

        // Ping user toggle
        const pingUserToggle = document.getElementById('embedPingUser');
        const userSelector = document.getElementById('embedUserSelector');
        if (pingUserToggle && userSelector) {
            pingUserToggle.addEventListener('change', (e) => {
                userSelector.style.display = e.target.checked ? 'block' : 'none';
            });
        }

        // Author toggle
        const authorToggle = document.getElementById('embedAuthorEnabled');
        const authorContainer = document.getElementById('embedAuthorContainer');
        if (authorToggle && authorContainer) {
            authorToggle.addEventListener('change', (e) => {
                authorContainer.style.display = e.target.checked ? 'block' : 'none';
                this.updateEmbedPreview();
            });
        }

        // Footer toggle
        const footerToggle = document.getElementById('embedFooterEnabled');
        const footerContainer = document.getElementById('embedFooterContainer');
        if (footerToggle && footerContainer) {
            footerToggle.addEventListener('change', (e) => {
                footerContainer.style.display = e.target.checked ? 'block' : 'none';
                this.updateEmbedPreview();
            });
        }

        // Fields toggle
        const fieldsToggle = document.getElementById('embedFieldsEnabled');
        const fieldsContainer = document.getElementById('embedFieldsContainer');
        if (fieldsToggle && fieldsContainer) {
            fieldsToggle.addEventListener('change', (e) => {
                fieldsContainer.style.display = e.target.checked ? 'block' : 'none';
                this.updateEmbedPreview();
            });
        }
    }

    initColorPicker() {
        const colorPicker = document.getElementById('embedColor');
        const colorPresets = document.querySelectorAll('.color-preset');

        if (colorPicker) {
            colorPicker.addEventListener('change', () => {
                this.updateEmbedPreview();
                // Update border color
                const embedPreview = document.querySelector('.discord-embed');
                if (embedPreview) {
                    embedPreview.style.borderLeftColor = colorPicker.value;
                }
            });
        }

        colorPresets.forEach(preset => {
            preset.addEventListener('click', () => {
                const color = preset.dataset.color;
                if (colorPicker) {
                    colorPicker.value = color;
                    this.updateEmbedPreview();
                    const embedPreview = document.querySelector('.discord-embed');
                    if (embedPreview) {
                        embedPreview.style.borderLeftColor = color;
                    }
                }
                
                // Update active state
                colorPresets.forEach(p => p.classList.remove('active'));
                preset.classList.add('active');
            });
        });
    }

    setupEmbedEventListeners() {
        // Update preview on all input changes
        const inputs = [
            'embedTitle', 'embedDescription', 'embedThumbnail', 'embedImage',
            'embedAuthorName', 'embedAuthorIcon', 'embedAuthorUrl',
            'embedFooterText', 'embedFooterIcon', 'embedTimestamp'
        ];

        inputs.forEach(id => {
            const element = document.getElementById(id);
            if (element) {
                element.addEventListener('input', () => this.updateEmbedPreview());
                if (element.type === 'checkbox') {
                    element.addEventListener('change', () => this.updateEmbedPreview());
                }
            }
        });

        // Add field button
        const addFieldBtn = document.getElementById('addEmbedField');
        if (addFieldBtn) {
            addFieldBtn.addEventListener('click', () => this.addEmbedField());
        }

        // Form submission
        const sendBtn = document.getElementById('sendEmbedBtn');
        if (sendBtn) {
            sendBtn.addEventListener('click', () => this.sendEmbedMessage());
        }

        // Preview refresh button
        const previewBtn = document.getElementById('previewEmbedBtn');
        if (previewBtn) {
            previewBtn.addEventListener('click', () => this.updateEmbedPreview());
        }

        // Clear button
        const clearBtn = document.getElementById('clearEmbedBtn');
        if (clearBtn) {
            clearBtn.addEventListener('click', () => this.clearEmbedForm());
        }
    }

    addEmbedField() {
        const fieldsList = document.getElementById('embedFieldsList');
        if (!fieldsList) return;

        const fieldItem = document.createElement('div');
        fieldItem.className = 'embed-field-item';
        fieldItem.innerHTML = `
            <div class="field-input-group">
                <label>Field Name</label>
                <input type="text" class="field-input form-control field-name" placeholder="Field name..." maxlength="256">
            </div>
            <div class="field-input-group">
                <label>Field Value</label>
                <textarea class="field-input form-control field-value" placeholder="Field value..." rows="3" maxlength="1024"></textarea>
            </div>
            <div class="field-toggle-wrapper">
                <div class="toggle-label-text">Inline</div>
                <div class="field-toggle-switch">
                    <input type="checkbox" class="field-inline">
                    <span class="field-toggle-slider"></span>
                </div>
            </div>
            <div class="field-actions">
                <button type="button" class="field-move-btn field-up" title="Move Up">
                    <i class="fas fa-chevron-up"></i>
                </button>
                <button type="button" class="field-remove-btn" title="Remove Field">
                    <i class="fas fa-trash"></i>
                </button>
            </div>
        `;

        // Add event listeners
        const removeBtn = fieldItem.querySelector('.field-remove-btn');
        removeBtn.addEventListener('click', () => {
            fieldItem.remove();
            this.updateEmbedPreview();
        });

        const upBtn = fieldItem.querySelector('.field-up');
        upBtn.addEventListener('click', () => {
            const prev = fieldItem.previousElementSibling;
            if (prev) {
                fieldsList.insertBefore(fieldItem, prev);
                this.updateEmbedPreview();
            }
        });

        // Input listeners
        const nameInput = fieldItem.querySelector('.field-name');
        const valueInput = fieldItem.querySelector('.field-value');
        const inlineToggle = fieldItem.querySelector('.field-inline');
        
        nameInput.addEventListener('input', () => this.updateEmbedPreview());
        valueInput.addEventListener('input', () => this.updateEmbedPreview());
        inlineToggle.addEventListener('change', () => this.updateEmbedPreview());

        // Toggle functionality
        const toggleSlider = fieldItem.querySelector('.field-toggle-slider');
        toggleSlider.addEventListener('click', () => {
            inlineToggle.checked = !inlineToggle.checked;
            this.updateEmbedPreview();
        });

        fieldsList.appendChild(fieldItem);
        this.updateEmbedPreview();
    }

    updateEmbedPreview() {
        const preview = document.getElementById('embedPreview');
        if (!preview) return;

        // Get form data
        const title = document.getElementById('embedTitle')?.value || '';
        const description = document.getElementById('embedDescription')?.value || '';
        const color = document.getElementById('embedColor')?.value || '#5865F2';
        const thumbnailUrl = document.getElementById('embedThumbnail')?.value || '';
        const imageUrl = document.getElementById('embedImage')?.value || '';
        
        // Author data
        const authorEnabled = document.getElementById('embedAuthorEnabled')?.checked || false;
        const authorName = document.getElementById('embedAuthorName')?.value || '';
        const authorIcon = document.getElementById('embedAuthorIcon')?.value || '';
        const authorUrl = document.getElementById('embedAuthorUrl')?.value || '';
        
        // Footer data
        const footerEnabled = document.getElementById('embedFooterEnabled')?.checked || false;
        const footerText = document.getElementById('embedFooterText')?.value || '';
        const footerIcon = document.getElementById('embedFooterIcon')?.value || '';
        const timestampEnabled = document.getElementById('embedTimestamp')?.checked || false;

        // Build preview HTML
        let html = '<div class="embed-content">';
        
        // Author
        if (authorEnabled && authorName) {
            html += '<div class="embed-author">';
            if (authorIcon) {
                html += `<img src="${authorIcon}" class="embed-author-icon" onerror="this.style.display='none'">`;
            }
            if (authorUrl) {
                html += `<a href="${authorUrl}" class="embed-author-name" target="_blank">${this.formatDiscordText(authorName)}</a>`;
            } else {
                html += `<span class="embed-author-name">${this.formatDiscordText(authorName)}</span>`;
            }
            html += '</div>';
        }

        // Title
        if (title) {
            html += `<div class="embed-title-preview">${this.formatDiscordText(title)}</div>`;
        }

        // Description
        if (description) {
            const formattedDescription = this.formatDiscordText(description).replace(/\n/g, '<br>');
            html += `<div class="embed-description-preview">${formattedDescription}</div>`;
        }

        // Fields
        const fieldsContainer = document.getElementById('embedFieldsList');
        if (fieldsContainer) {
            const fields = fieldsContainer.querySelectorAll('.embed-field-item');
            if (fields.length > 0) {
                html += '<div class="embed-fields">';
                fields.forEach(field => {
                    const name = field.querySelector('.field-name')?.value || '';
                    const value = field.querySelector('.field-value')?.value || '';
                    const inline = field.querySelector('.field-inline')?.checked || false;
                    
                    if (name && value) {
                        const formattedName = this.formatDiscordText(name);
                        const formattedValue = this.formatDiscordText(value).replace(/\n/g, '<br>');
                        html += `
                            <div class="embed-field ${inline ? 'inline' : ''}">
                                <div class="embed-field-name">${formattedName}</div>
                                <div class="embed-field-value">${formattedValue}</div>
                            </div>
                        `;
                    }
                });
                html += '</div>';
            }
        }

        html += '</div>';

        // Image
        if (imageUrl) {
            html += `<img src="${imageUrl}" class="embed-image" onerror="this.style.display='none'">`;
        }

        // Thumbnail
        if (thumbnailUrl) {
            html = `<img src="${thumbnailUrl}" class="embed-thumbnail" onerror="this.style.display='none'">${html}`;
        }

        // Footer
        if (footerEnabled && (footerText || timestampEnabled)) {
            html += '<div class="embed-footer">';
            if (footerIcon) {
                html += `<img src="${footerIcon}" class="embed-footer-icon" onerror="this.style.display='none'">`;
            }
            if (footerText) {
                html += `<span class="embed-footer-text">${this.formatDiscordText(footerText)}</span>`;
            }
            if (timestampEnabled) {
                const now = new Date().toLocaleString();
                html += `<span class="embed-timestamp">${footerText ? ' • ' : ''}${now}</span>`;
            }
            html += '</div>';
        }

        preview.innerHTML = html;
        preview.style.borderLeftColor = color;
    }

    async sendEmbedMessage() {
        if (!this.currentGuild) {
            this.showError('Please select a server first.');
            return;
        }

        // Get target channel
        const targetChannel = document.getElementById('embedTargetChannel')?.value;
        if (!targetChannel) {
            this.showError('Please select a target channel.');
            return;
        }

        // Validate that we have either title or description
        const title = document.getElementById('embedTitle')?.value || '';
        const description = document.getElementById('embedDescription')?.value || '';
        
        if (!title && !description) {
            this.showError('Please provide at least a title or description for the embed.');
            return;
        }

        try {
            // Show loading state
            const sendBtn = document.getElementById('sendEmbedBtn');
            const originalText = sendBtn.innerHTML;
            sendBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Sending...';
            sendBtn.disabled = true;

            // Collect form data
            const embedData = {
                target_channel: targetChannel,
                title: title || null,
                description: description || null,
                color: document.getElementById('embedColor')?.value || '#5865F2',
                thumbnail_url: document.getElementById('embedThumbnail')?.value || null,
                image_url: document.getElementById('embedImage')?.value || null
            };

            // Ping settings
            if (document.getElementById('embedPingRole')?.checked) {
                embedData.ping_role_id = document.getElementById('embedPingRoleSelect')?.value || null;
            }
            if (document.getElementById('embedPingUser')?.checked) {
                embedData.ping_user_id = document.getElementById('embedPingUserSelect')?.value || null;
            }

            // Author settings
            if (document.getElementById('embedAuthorEnabled')?.checked) {
                embedData.author_name = document.getElementById('embedAuthorName')?.value || null;
                embedData.author_icon_url = document.getElementById('embedAuthorIcon')?.value || null;
                embedData.author_url = document.getElementById('embedAuthorUrl')?.value || null;
            }

            // Footer settings
            if (document.getElementById('embedFooterEnabled')?.checked) {
                embedData.footer_text = document.getElementById('embedFooterText')?.value || null;
                embedData.footer_icon_url = document.getElementById('embedFooterIcon')?.value || null;
                embedData.timestamp_enabled = document.getElementById('embedTimestamp')?.checked || false;
            }

            // Fields
            if (document.getElementById('embedFieldsEnabled')?.checked) {
                const fields = [];
                const fieldItems = document.querySelectorAll('#embedFieldsList .embed-field-item');
                fieldItems.forEach(item => {
                    const name = item.querySelector('.field-name')?.value?.trim();
                    const value = item.querySelector('.field-value')?.value?.trim();
                    const inline = item.querySelector('.field-inline')?.checked || false;
                    
                    if (name && value) {
                        fields.push({ name, value, inline });
                    }
                });
                embedData.fields = fields.length > 0 ? fields : null;
            }

            // Send the embed
            const response = await this.apiCall(`/guild/${this.currentGuild}/embed/send`, 'POST', embedData);
            
            this.showSuccess('Embed sent successfully!');
            
            // Optionally clear form or keep it for reuse
            // this.clearEmbedForm();

        } catch (error) {
            console.error('Failed to send embed:', error);
            this.showError(error.message || 'Failed to send embed. Please try again.');
        } finally {
            // Restore button state
            const sendBtn = document.getElementById('sendEmbedBtn');
            sendBtn.innerHTML = originalText;
            sendBtn.disabled = false;
        }
    }

    clearEmbedForm() {
        // Clear all form fields
        const inputs = [
            'embedTargetChannel', 'embedTitle', 'embedDescription', 'embedThumbnail', 'embedImage',
            'embedAuthorName', 'embedAuthorIcon', 'embedAuthorUrl',
            'embedFooterText', 'embedFooterIcon'
        ];

        inputs.forEach(id => {
            const element = document.getElementById(id);
            if (element) {
                element.value = '';
            }
        });

        // Reset checkboxes
        const checkboxes = [
            'embedPingRole', 'embedPingUser', 'embedAuthorEnabled', 
            'embedFooterEnabled', 'embedTimestamp', 'embedFieldsEnabled'
        ];

        checkboxes.forEach(id => {
            const element = document.getElementById(id);
            if (element) {
                element.checked = false;
            }
        });

        // Reset color
        const colorPicker = document.getElementById('embedColor');
        if (colorPicker) {
            colorPicker.value = '#5865F2';
        }

        // Clear fields
        const fieldsList = document.getElementById('embedFieldsList');
        if (fieldsList) {
            fieldsList.innerHTML = '';
        }

        // Hide containers
        const containers = [
            'embedRoleSelector', 'embedUserSelector', 'embedAuthorContainer',
            'embedFooterContainer', 'embedFieldsContainer'
        ];

        containers.forEach(id => {
            const element = document.getElementById(id);
            if (element) {
                element.style.display = 'none';
            }
        });

        // Update preview
        this.updateEmbedPreview();
        
        this.showSuccess('Form cleared successfully!');
    }

    async loadEmbedCreatorData() {
        console.log('🔄 Loading embed creator data...');
        console.log('📊 Current data state:', {
            channels: this.channels ? this.channels.length : 'null',
            roles: this.roles ? this.roles.length : 'null',
            members: this.members ? this.members.length : 'null'
        });
        
        // Load channels for target selection
        if (!this.channels) {
            console.log('📺 Loading channels...');
            await this.loadGuildChannels();
        }
        
        // Load roles for ping selection
        if (!this.roles) {
            console.log('🎭 Loading roles...');
            await this.loadGuildRoles();
        }
        
        // Load members for ping selection
        if (!this.members) {
            console.log('👥 Loading members...');
            await this.loadGuildMembers();
        }
        
        console.log('✅ Data loaded, populating selectors...');
        console.log('📊 Final data state:', {
            channels: this.channels ? this.channels.length : 'null',
            roles: this.roles ? this.roles.length : 'null',
            members: this.members ? this.members.length : 'null'
        });
        
        // Populate selectors
        this.populateEmbedChannelSelector();
        this.populateEmbedRoleSelector();
        this.populateEmbedMemberSelector();
        
        console.log('🎯 Embed creator data loading complete');
    }

    // Format Discord text (bold, italic, underline, etc.)
    formatDiscordText(text) {
        if (!text) return text;
        
        // Escape HTML first to prevent XSS
        text = text.replace(/&/g, '&amp;')
                  .replace(/</g, '&lt;')
                  .replace(/>/g, '&gt;')
                  .replace(/"/g, '&quot;')
                  .replace(/'/g, '&#39;');
        
        // Apply Discord formatting
        // **bold**
        text = text.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
        
        // *italic*
        text = text.replace(/\*([^*]+)\*/g, '<em>$1</em>');
        
        // __underline__
        text = text.replace(/__([^_]+)__/g, '<u>$1</u>');
        
        // ~~strikethrough~~
        text = text.replace(/~~([^~]+)~~/g, '<del>$1</del>');
        
        // `code`
        text = text.replace(/`([^`]+)`/g, '<code class="discord-inline-code">$1</code>');
        
        // ```code block```
        text = text.replace(/```([^`]+)```/g, '<pre class="discord-code-block">$1</pre>');
        
        // > quote
        text = text.replace(/^> (.+)$/gm, '<div class="discord-quote">$1</div>');
        
        return text;
    }

    populateEmbedChannelSelector() {
        console.log('📺 Populating embed channel selector...');
        const channelSelect = document.getElementById('embedTargetChannel');
        console.log('📺 Channel select element:', channelSelect ? 'FOUND' : 'NOT FOUND');
        console.log('📺 Channels data:', this.channels ? `${this.channels.length} channels` : 'NO DATA');
        
        if (!channelSelect || !this.channels) {
            console.log('❌ Cannot populate channel selector - missing element or data');
            return;
        }

        channelSelect.innerHTML = '<option value="">Select a channel...</option>';
        
        // For the bulk data, all channels are already text channels (type 0)
        // so we don't need to filter by type anymore
        console.log('📺 All channels available:', this.channels.length);
        
        this.channels.forEach(channel => {
            const option = document.createElement('option');
            option.value = channel.id;
            option.textContent = `# ${channel.name}`;
            channelSelect.appendChild(option);
        });
        
        console.log('✅ Channel selector populated with', this.channels.length, 'channels');
    }

    populateEmbedRoleSelector() {
        const roleSelect = document.getElementById('embedPingRoleSelect');
        if (!roleSelect || !this.roles) return;

        roleSelect.innerHTML = '<option value="">Select a role...</option>';
        
        // Filter out @everyone and managed roles
        const availableRoles = this.roles.filter(role => 
            role.name !== '@everyone' && !role.managed
        );
        
        availableRoles.forEach(role => {
            const option = document.createElement('option');
            option.value = role.id;
            option.textContent = role.name;
            roleSelect.appendChild(option);
        });
    }

    populateEmbedMemberSelector() {
        console.log('👥 Populating embed member selector...');
        const memberSelect = document.getElementById('embedPingUserSelect');
        console.log('👥 Member select element:', memberSelect ? 'FOUND' : 'NOT FOUND');
        console.log('👥 Members data:', this.members ? `${this.members.length} members` : 'NO DATA');
        
        if (!memberSelect || !this.members) {
            console.log('❌ Cannot populate member selector - missing element or data');
            return;
        }

        memberSelect.innerHTML = '<option value="">Select a member...</option>';
        
        // Limit to first 100 members to avoid performance issues
        const membersToShow = this.members.slice(0, 100);
        console.log('👥 Members to show:', membersToShow.length);
        
        membersToShow.forEach(member => {
            const option = document.createElement('option');
            // The member API returns: {id, username, display_name, avatar, joined_at}
            // Not: {user: {id, username}, nick}
            option.value = member.id;
            option.textContent = member.display_name || member.username;
            memberSelect.appendChild(option);
        });
        
        if (this.members.length > 100) {
            const option = document.createElement('option');
            option.disabled = true;
            option.textContent = `... and ${this.members.length - 100} more members`;
            memberSelect.appendChild(option);
        }
        
        console.log('✅ Member selector populated with', membersToShow.length, 'members');
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
                
                // Load section-specific data
                if (targetId === 'welcome' && window.dashboard) {
                    console.log('🚀 Loading welcome settings...');
                    window.dashboard.loadWelcomeSettings().catch(error => {
                        console.error('Failed to load welcome settings:', error);
                    });
                }
                
                if (targetId === 'tickets' && window.dashboard) {
                    console.log('🚀 Loading ticket settings...');
                    window.dashboard.loadTicketSettings().catch(error => {
                        console.error('Failed to load ticket settings:', error);
                    });
                }
                
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
    
    // Setup tab change listener for role menus
    setTimeout(() => {
        // Listen for tab changes to render role menus when tab becomes active
        const roleMenusLink = document.querySelector('a[href="#role-menus"]');
        if (roleMenusLink) {
            roleMenusLink.addEventListener('click', () => {
                console.log('🔄 Role menus tab clicked, checking for cached data');
                setTimeout(() => {
                    if (dashboard.cachedRoleMenus) {
                        console.log('📋 Found cached role menus, rendering now');
                        dashboard.renderRoleMenusNow(dashboard.cachedRoleMenus);
                    }
                }, 100); // Small delay to ensure tab is active
            });
            console.log('✅ Role menus tab listener added');
        }
        
        // Also listen for Bootstrap tab events if available
        const roleMenusTab = document.getElementById('role-menus');
        if (roleMenusTab) {
            roleMenusTab.addEventListener('shown.bs.tab', () => {
                console.log('🔄 Role menus tab shown via Bootstrap event');
                if (dashboard.cachedRoleMenus) {
                    console.log('📋 Found cached role menus, rendering via Bootstrap event');
                    dashboard.renderRoleMenusNow(dashboard.cachedRoleMenus);
                }
            });
            console.log('✅ Bootstrap tab listener added');
        }
        
        // Listen for XP settings tab to load roles for level roles
        const xpTab = document.getElementById('xp-settings');
        if (xpTab) {
            xpTab.addEventListener('shown.bs.tab', async () => {
                console.log('🔄 XP settings tab shown - loading roles for level roles');
                if (!dashboard.roles) {
                    await dashboard.loadGuildRoles();
                }
                // Update level roles display after roles are loaded
                await dashboard.updateLevelRolesDisplay();
            });
            console.log('✅ XP tab listener added');
        }
    }, 200);
    
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
    
    // Setup reset XP button
    const resetXPBtn = document.getElementById('resetXPBtn');
    if (resetXPBtn) {
        resetXPBtn.addEventListener('click', () => dashboard.resetServerXP());
    }
    
    // Setup add level role button
    const addLevelRoleBtn = document.getElementById('addLevelRoleBtn');
    if (addLevelRoleBtn) {
        addLevelRoleBtn.addEventListener('click', () => dashboard.addLevelRoleItem());
    }
    
    // Setup create role menu button
    const createRoleMenuBtn = document.getElementById('createRoleMenuBtn');
    if (createRoleMenuBtn) {
        createRoleMenuBtn.addEventListener('click', () => dashboard.createRoleMenu());
    }

    // Add refresh button event listener
    const refreshRoleMenusBtn = document.getElementById('refreshRoleMenusBtn');
    if (refreshRoleMenusBtn) {
        refreshRoleMenusBtn.addEventListener('click', async () => {
            console.log('🔄 Manual refresh of role menus triggered');
            
            if (!dashboard.currentGuild) {
                console.warn('No guild selected for refresh');
                dashboard.showError('Please select a server first');
                return;
            }
            
            // Add loading state
            const originalIcon = refreshRoleMenusBtn.querySelector('i');
            const originalText = originalIcon ? '' : refreshRoleMenusBtn.textContent;
            
            if (originalIcon) {
                originalIcon.className = 'fas fa-spinner fa-spin';
            } else {
                refreshRoleMenusBtn.textContent = 'Refreshing...';
            }
            refreshRoleMenusBtn.disabled = true;
            
            try {
                console.log(`Refreshing role menus for guild: ${dashboard.currentGuild}`);
                await dashboard.loadRoleMenus();
                console.log('✅ Role menus refreshed successfully');
            } catch (error) {
                console.error('❌ Failed to refresh role menus:', error);
                dashboard.showError('Failed to refresh role menus');
            } finally {
                // Restore original state
                if (originalIcon) {
                    originalIcon.className = 'fas fa-sync-alt';
                } else {
                    refreshRoleMenusBtn.textContent = originalText;
                }
                refreshRoleMenusBtn.disabled = false;
            }
        });
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
    
    // Setup welcome fields toggle
    const welcomeFieldsToggle = document.getElementById('welcomeFields');
    const welcomeFieldsContainer = document.getElementById('welcomeFieldsContainer');
    if (welcomeFieldsToggle && welcomeFieldsContainer) {
        welcomeFieldsToggle.addEventListener('change', (e) => {
            welcomeFieldsContainer.style.display = e.target.checked ? 'block' : 'none';
        });
    }
    
    // Setup goodbye fields toggle
    const goodbyeFieldsToggle = document.getElementById('goodbyeFields');
    const goodbyeFieldsContainer = document.getElementById('goodbyeFieldsContainer');
    if (goodbyeFieldsToggle && goodbyeFieldsContainer) {
        goodbyeFieldsToggle.addEventListener('change', (e) => {
            goodbyeFieldsContainer.style.display = e.target.checked ? 'block' : 'none';
        });
    }

    // Setup add field buttons
    const addWelcomeFieldBtn = document.getElementById('addWelcomeField');
    if (addWelcomeFieldBtn) {
        addWelcomeFieldBtn.addEventListener('click', () => {
            const welcomeFieldsList = document.getElementById('welcomeFieldsList');
            const fieldItem = dashboard.createFieldItem('', '', false, welcomeFieldsList);
            welcomeFieldsList.appendChild(fieldItem);
            dashboard.updateFieldMoveButtons(welcomeFieldsList);
        });
    }

    const addGoodbyeFieldBtn = document.getElementById('addGoodbyeField');
    if (addGoodbyeFieldBtn) {
        addGoodbyeFieldBtn.addEventListener('click', () => {
            const goodbyeFieldsList = document.getElementById('goodbyeFieldsList');
            const fieldItem = dashboard.createFieldItem('', '', false, goodbyeFieldsList);
            goodbyeFieldsList.appendChild(fieldItem);
            dashboard.updateFieldMoveButtons(goodbyeFieldsList);
        });
    }

    // Setup embed creator tab listener
    const embedTab = document.getElementById('embed');
    if (embedTab) {
        embedTab.addEventListener('shown.bs.tab', async () => {
            console.log('🎨 Embed creator tab shown - initializing...');
            console.log('🔍 Current embed data loaded status:', dashboard.dataLoaded?.embed);
            
            // Always load data for embed creator to ensure it works
            await dashboard.loadEmbedCreatorData();
            await dashboard.initEmbedCreator();
            dashboard.dataLoaded.embed = true;
            
            console.log('✅ Embed creator initialization complete');
        });
    }

    // Also listen for simple navigation clicks
    const embedNavLink = document.querySelector('a[href="#embed"]');
    if (embedNavLink) {
        embedNavLink.addEventListener('click', async () => {
            console.log('🎨 Embed creator nav clicked - initializing...');
            setTimeout(async () => {
                console.log('🔍 Current embed data loaded status:', dashboard.dataLoaded?.embed);
                
                // Always load data for embed creator to ensure it works
                await dashboard.loadEmbedCreatorData();
                await dashboard.initEmbedCreator();
                dashboard.dataLoaded.embed = true;
                
                console.log('✅ Embed creator click initialization complete');
            }, 100);
        });
    }
});

// Make dashboard globally available for debugging
window.dashboard = dashboard;
