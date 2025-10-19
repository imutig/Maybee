// Maybee Dashboard JavaScript
console.log('📜 Dashboard.js script loaded!');

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
        // Chart manager
        this.chartManager = null;
        this.init();
    }

    async init() {
        try {
            console.log('🚀 Starting dashboard initialization...');
            // Get access token from cookie
            const token = this.getCookie('access_token');
            if (!token) {
                console.log('❌ No access token found, redirecting to login');
                window.location.href = '/';
                return;
            }
            console.log('✅ Access token found');

            // Use language data from backend if available, otherwise load from API
            if (window.langData && window.currentLang && window.supportedLanguages) {
                console.log('✅ Using language data from backend');
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
                console.log('⚠️ Using fallback language loading method');
                // Fallback to old method
                await this.loadAvailableLanguages();
                await this.loadUserLanguage();
                await this.loadLanguageStrings();
                this.initLanguageSelector();
                this.updateUILanguage();
            }
            
            // Load user data
            console.log('👤 Loading user data...');
            await this.loadUser();
            console.log('🏰 Loading guilds...');
            await this.loadGuilds();
            
            // Initialize chart manager
            if (typeof ChartManager !== 'undefined') {
                this.chartManager = new ChartManager(this);
                this.chartManager.initChartEventListeners();
                console.log('✅ ChartManager initialized successfully');
            } else {
                console.warn('⚠️ ChartManager not available, skipping chart initialization');
            }
            
            // Setup navigation with a small delay to ensure DOM is ready
            console.log('🧭 Setting up navigation...');
            setTimeout(() => {
                setupModernNavigation();
                this.setupRoleMenuButtons();
                setupLevelUpEventListeners();
            }, 100);
            
            // Hide loading overlay
            console.log('🎉 Dashboard initialization complete!');
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
            if (this.chartManager) {
                this.chartManager.clearCharts(); // Clear existing charts
            }
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
            
            // Load charts after guild data is loaded
            if (this.chartManager) {
                this.chartManager.loadCharts();
            }
            
            // Show/hide Feur Mode card based on guild ID
            const feurModeCard = document.getElementById('feurModeCard');
            if (feurModeCard) {
                if (guildId === '1279486672261746809') {
                    feurModeCard.style.display = 'block';
                    await this.loadFeurMode();
                } else {
                    feurModeCard.style.display = 'none';
                }
            }
            
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
                    <p data-translate="xp_system.no_level_roles">No level roles configured yet. Click "Add Level Role" to get started!</p>
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
                           placeholder="Level" min="1" value="" data-translate="xp_system.level_placeholder">
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
                       placeholder="Level" min="1" value="${levelRole.level}" data-translate="xp_system.level_placeholder">
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

            // Save both XP settings and level-up message config
            await Promise.all([
                this.apiCall(`/guild/${this.currentGuild}/xp`, 'PUT', xpConfig),
                this.saveLevelUpConfig()
            ]);
            
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

    setupRoleMenuButtons() {
        console.log('🔧 Setting up role menu buttons...');
        
        // Refresh button
        const refreshBtn = document.getElementById('refreshRoleMenusBtn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => {
                console.log('🔄 Refresh role menus button clicked');
                this.loadRoleMenus();
            });
            console.log('✅ Refresh button event listener added');
        } else {
            console.warn('⚠️ Refresh button not found');
        }
        
        // Create button
        const createBtn = document.getElementById('createRoleMenuBtn');
        if (createBtn) {
            createBtn.addEventListener('click', () => {
                console.log('➕ Create role menu button clicked');
                this.showRoleMenuModal();
            });
            console.log('✅ Create button event listener added');
        } else {
            console.warn('⚠️ Create button not found');
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
                        <button class="action-btn-small" onclick="window.dashboard.sendRoleMenu(${menu.id})" style="background: #28a745; border-color: #28a745;">
                            <i class="fas fa-paper-plane"></i>
                            Send
                        </button>
                        <button class="action-btn-small" onclick="window.dashboard.editRoleMenu(${menu.id})">
                            <i class="fas fa-edit"></i>
                            Edit
                        </button>
                        <button class="action-btn-small" onclick="window.dashboard.deleteRoleMenu(${menu.id})" style="background: #dc3545; border-color: #dc3545;">
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
            const response = await this.apiCall(`/guild/${this.currentGuild}/role-menus/${menuId}/send`, 'POST');
            console.log(`✅ Send API call successful for menu ${menuId}`);
            
            // Check if the message was actually created
            if (response.message && response.message.includes('Message ID:')) {
                this.showSuccess(response.message);
            } else {
                this.showSuccess('Role menu sent to Discord channel successfully!');
            }
            
            // Refresh the role menus list to show updated status
            setTimeout(() => {
                this.loadRoleMenus();
            }, 1000);
            
        } catch (error) {
            console.error('❌ Failed to send role menu:', error);
            let errorMessage = 'Failed to send role menu. Please try again.';
            
            if (error.response && error.response.data && error.response.data.detail) {
                errorMessage = `Error: ${error.response.data.detail}`;
            }
            
            this.showError(errorMessage);
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
                                           placeholder="Select Your Role" required maxlength="256" data-translate="role_menus.select_role_placeholder">
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
                                              placeholder="Choose a role from the dropdown below" data-translate="role_menus.description_placeholder">${isEdit ? this.escapeHtml(menu.description || '') : ''}</textarea>
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
            document.getElementById('welcomeImageUrl').value = config.welcome_image_url || '';
            
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
            document.getElementById('goodbyeImageUrl').value = config.goodbye_image_url || '';
            
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

    async loadLevelUpConfig() {
        if (!this.currentGuild) return;

        try {
            const config = await this.apiCall(`/guild/${this.currentGuild}/level-up-config`);
            // Set the channel select value
            // Set the channel select value after a short delay to ensure options are loaded
            const levelUpChannelSelect = document.getElementById('levelUpChannel');
            const setChannelValue = () => {
                if (!config.channel_id) return;
                // Try to set value, if not present, add it
                if ([...levelUpChannelSelect.options].some(opt => opt.value === String(config.channel_id))) {
                    levelUpChannelSelect.value = String(config.channel_id);
                } else {
                    // Add the option if missing (should not happen, but fallback)
                    const opt = document.createElement('option');
                    opt.value = String(config.channel_id);
                    opt.textContent = `#Salon ${config.channel_id}`;
                    levelUpChannelSelect.appendChild(opt);
                    levelUpChannelSelect.value = String(config.channel_id);
                }
            };
            setTimeout(setChannelValue, 100);
            // Message type
            document.getElementById('levelUpMessageType').value = config.message_type || 'embed';
            // Simple message
            document.getElementById('levelUpSimpleMessage').value = config.message_content || 'Congratulations {user}! You have reached level {level}!';
            // Embed configuration
            document.getElementById('levelUpEmbedTitle').value = config.embed_title || 'Level Up!';
            document.getElementById('levelUpEmbedDescription').value = config.embed_description || '{user} has reached level **{level}**!';
            document.getElementById('levelUpEmbedColor').value = config.embed_color || '#FFD700';
            document.getElementById('levelUpEmbedThumbnail').value = config.embed_thumbnail_url || '';
            document.getElementById('levelUpShowUserAvatar').checked = config.show_user_avatar !== false;
            document.getElementById('levelUpEmbedImage').value = config.embed_image_url || '';
            document.getElementById('levelUpEmbedFooter').value = config.embed_footer_text || 'Keep up the great work!';
            document.getElementById('levelUpEmbedTimestamp').checked = config.embed_timestamp !== false;
            // Toggle visibility based on message type
            this.toggleLevelUpMessageType();
        } catch (error) {
            console.error('Failed to load level up config:', error);
        }
    }

    toggleLevelUpMessageType() {
        const messageType = document.getElementById('levelUpMessageType').value;
        const simpleGroup = document.getElementById('simpleMessageGroup');
        const embedGroup = document.getElementById('embedConfigGroup');
        
        if (messageType === 'simple') {
            simpleGroup.style.display = 'block';
            embedGroup.style.display = 'none';
        } else {
            simpleGroup.style.display = 'none';
            embedGroup.style.display = 'block';
        }
    }

    async saveLevelUpConfig() {
        if (!this.currentGuild) {
            return; // Silent fail, will be caught by saveXPSettings
        }

        try {
            const config = {
                enabled: true,
                channel_id: document.getElementById('levelUpChannel').value || null,
                message_type: document.getElementById('levelUpMessageType').value,
                message_content: document.getElementById('levelUpSimpleMessage').value || 'Congratulations {user}! You have reached level {level}!',
                embed_title: document.getElementById('levelUpEmbedTitle').value || 'Level Up!',
                embed_description: document.getElementById('levelUpEmbedDescription').value || '{user} has reached level **{level}**!',
                embed_color: document.getElementById('levelUpEmbedColor').value || '#FFD700',
                embed_thumbnail_url: document.getElementById('levelUpEmbedThumbnail').value || null,
                show_user_avatar: document.getElementById('levelUpShowUserAvatar').checked,
                embed_image_url: document.getElementById('levelUpEmbedImage').value || null,
                embed_footer_text: document.getElementById('levelUpEmbedFooter').value || 'Keep up the great work!',
                embed_timestamp: document.getElementById('levelUpEmbedTimestamp').checked
            };

            await this.apiCall(`/guild/${this.currentGuild}/level-up-config`, 'PUT', config);
            // Success message will be shown by saveXPSettings
            
        } catch (error) {
            console.error('Failed to save level up config:', error);
            throw error; // Re-throw to be caught by saveXPSettings
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
                welcome_image_url: document.getElementById('welcomeImageUrl').value || null,
                goodbye_enabled: document.getElementById('goodbyeEnabled').checked,
                goodbye_channel: document.getElementById('goodbyeChannel').value || null,
                goodbye_title: document.getElementById('goodbyeTitle').value || '👋 Departure',
                goodbye_message: document.getElementById('goodbyeMessage').value || 'Goodbye {user}, thanks for being part of {server}!',
                goodbye_fields: goodbyeFields,
                goodbye_image_url: document.getElementById('goodbyeImageUrl').value || null,
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

    // Feur Mode Methods
    async loadFeurMode() {
        if (!this.currentGuild) return;
        
        try {
            const data = await this.apiCall(`/guild/${this.currentGuild}/feur-mode`);
            const checkbox = document.getElementById('feurModeEnabled');
            if (checkbox) {
                checkbox.checked = data.enabled || false;
            }
        } catch (error) {
            console.error('Error loading Feur mode:', error);
        }
    }

    async toggleFeurMode(enabled) {
        if (!this.currentGuild) return;
        
        try {
            const response = await this.apiCall(
                `/guild/${this.currentGuild}/feur-mode?enabled=${enabled}`,
                'POST'
            );
            
            if (response.success) {
                this.showSuccess(response.message);
            } else {
                this.showError('Erreur lors de la mise à jour du mode Feur');
            }
        } catch (error) {
            console.error('Error toggling Feur mode:', error);
            this.showError('Erreur lors de la mise à jour du mode Feur');
            
            // Revert checkbox state on error
            const checkbox = document.getElementById('feurModeEnabled');
            if (checkbox) {
                checkbox.checked = !enabled;
            }
        }
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
        await this.loadLevelUpConfig();  // Load level-up message configuration
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

        // Ensure roles are loaded in the selector
        this.loadRolesForAutoRole();
    }

    async loadRolesForAutoRole() {
        const roleSelect = document.getElementById('roleSelect');
        if (!roleSelect) {
            console.warn('roleSelect element not found');
            return;
        }

        if (!this.currentGuild) {
            console.log('❌ No current guild for auto-role loading');
            return;
        }

        try {
            console.log(`📡 Loading roles for auto-role selector in guild ${this.currentGuild}`);
            const response = await this.apiCall(`/guild/${this.currentGuild}/roles`);
            const roles = response.roles || [];
            console.log(`✅ Received ${roles.length} roles for auto-role selector`);
            
            // Clear existing options except the first one
            while (roleSelect.children.length > 1) {
                roleSelect.removeChild(roleSelect.lastChild);
            }
            
            // Add role options (exclude @everyone and bot roles)
            roles.forEach(role => {
                if (role.name !== '@everyone' && !role.managed) {
                    const option = document.createElement('option');
                    option.value = role.id;
                    option.textContent = role.name;
                    roleSelect.appendChild(option);
                }
            });
            
            console.log(`✅ Added ${roles.filter(r => r.name !== '@everyone' && !r.managed).length} roles to auto-role selector`);
        } catch (error) {
            console.error('❌ Failed to load roles for auto-role selector:', error);
            roleSelect.innerHTML = '<option value="">Error loading roles...</option>';
        }
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
        
        // Populate verification role selects
        this.populateVerificationRoleSelects();
        
        // Populate verification channel select
        this.populateVerificationChannelSelect();
        
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

        // Populate verification role selects first
        this.populateVerificationRoleSelects();
        
        // Populate verification channel select
        this.populateVerificationChannelSelect();

        // Verification options
        document.getElementById('panelVerification').checked = panelData.verification_enabled || false;
        
        // Show/hide verification options based on checkbox
        document.getElementById('verificationOptions').style.display = panelData.verification_enabled ? 'block' : 'none';
        
        // Set verifier role (after populate)
        setTimeout(() => {
            document.getElementById('verifierRole').value = panelData.verifier_role_id || '';
        }, 100);
        
        // Set roles to remove (after populate)
        if (Array.isArray(panelData.roles_to_remove)) {
            setTimeout(() => {
                const rolesToRemove = document.getElementById('rolesToRemove');
                if (rolesToRemove) {
                    Array.from(rolesToRemove.options).forEach(opt => {
                        opt.selected = panelData.roles_to_remove.includes(opt.value);
                    });
                }
            }, 100);
        }
        
        // Set roles to add (after populate)
        if (Array.isArray(panelData.roles_to_add)) {
            setTimeout(() => {
                const rolesToAdd = document.getElementById('rolesToAdd');
                if (rolesToAdd) {
                    Array.from(rolesToAdd.options).forEach(opt => {
                        opt.selected = panelData.roles_to_add.includes(opt.value);
                    });
                }
            }, 100);
        }
        
        // Channel and message (after populate)
        setTimeout(() => {
            document.getElementById('verificationChannel').value = panelData.verification_channel || '';
            document.getElementById('verificationMessage').value = panelData.verification_message || '';
            document.getElementById('verificationImageUrl').value = panelData.verification_image_url || '';
        }, 100);

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
                buttons: [],
                verification_enabled: document.getElementById('panelVerification').checked,
                verifier_role_id: document.getElementById('verifierRole').value || null,
                roles_to_remove: Array.from(document.getElementById('rolesToRemove').selectedOptions).map(opt => opt.value),
                roles_to_add: Array.from(document.getElementById('rolesToAdd').selectedOptions).map(opt => opt.value),
                verification_channel: document.getElementById('verificationChannel').value,
                verification_message: document.getElementById('verificationMessage').value,
                verification_image_url: document.getElementById('verificationImageUrl').value || null
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

    populateVerificationRoleSelects() {
        const rolesToRemove = document.getElementById('rolesToRemove');
        const rolesToAdd = document.getElementById('rolesToAdd');
        const verifierRole = document.getElementById('verifierRole');
        
        if (!rolesToRemove || !rolesToAdd || !verifierRole) {
            console.warn('Verification role selects not found');
            return;
        }
        
        // Clear existing options
        rolesToRemove.innerHTML = '';
        rolesToAdd.innerHTML = '';
        verifierRole.innerHTML = '<option value="">Aucun (tous les modérateurs peuvent vérifier)</option>';
        
        // Populate with available roles
        if (this.roles && this.roles.length > 0) {
            this.roles.forEach(role => {
                if (role.name !== '@everyone' && !role.managed) {
                    // Add to "remove" select
                    const optionRemove = document.createElement('option');
                    optionRemove.value = role.id;
                    optionRemove.textContent = role.name;
                    rolesToRemove.appendChild(optionRemove);
                    
                    // Add to "add" select
                    const optionAdd = document.createElement('option');
                    optionAdd.value = role.id;
                    optionAdd.textContent = role.name;
                    rolesToAdd.appendChild(optionAdd);
                    
                    // Add to "verifier" select
                    const optionVerifier = document.createElement('option');
                    optionVerifier.value = role.id;
                    optionVerifier.textContent = role.name;
                    verifierRole.appendChild(optionVerifier);
                }
            });
        }
    }

    populateVerificationChannelSelect() {
        const verificationChannel = document.getElementById('verificationChannel');
        
        if (!verificationChannel) {
            console.warn('Verification channel select not found');
            return;
        }
        
        // Clear existing options except first
        verificationChannel.innerHTML = '<option value="">Sélectionner un salon...</option>';
        
        // Populate with available channels
        if (this.channels && this.channels.length > 0) {
            this.channels.forEach(channel => {
                const option = document.createElement('option');
                option.value = channel.id;
                option.textContent = `# ${channel.name}`;
                verificationChannel.appendChild(option);
            });
        }
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

    // Ticket Logs Methods
    async initTicketLogs() {
        console.log('📋 Initializing ticket logs system...');
        
        // Vérifier qu'un serveur est sélectionné
        if (!this.currentGuild) {
            console.log('❌ No guild selected for ticket logs');
            this.showError('Veuillez d\'abord sélectionner un serveur');
            return;
        }
        
        // Clear previous state
        this.selectedUser = null;
        this.userTickets = [];
        
        // Hide sections initially
        document.getElementById('userResultsSection').style.display = 'none';
        document.getElementById('userTicketsSection').style.display = 'none';
        
        // Setup search input event listener
        const searchInput = document.getElementById('userSearchInput');
        if (searchInput) {
            searchInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    this.searchUser();
                }
            });
            
            // Setup suggestions dropdown
            this.setupSearchSuggestions(searchInput);
        }
        
        // Load initial suggestions
        await this.loadSearchSuggestions();
        
        // Debug: Check if we have data
        await this.debugTicketLogs();
        
        console.log('✅ Ticket logs system initialized');
    }
    
    setupSearchSuggestions(searchInput) {
        let suggestionsContainer = null;
        let currentSuggestions = [];
        
        // Create suggestions container
        const createSuggestionsContainer = () => {
            if (suggestionsContainer) return;
            
            suggestionsContainer = document.createElement('div');
            suggestionsContainer.className = 'search-suggestions';
            suggestionsContainer.style.cssText = `
                position: absolute;
                top: 100%;
                left: 0;
                right: 0;
                background: var(--surface-dark);
                border: 1px solid var(--border-subtle);
                border-radius: 8px;
                box-shadow: var(--shadow-lg);
                z-index: 1000;
                max-height: 200px;
                overflow-y: auto;
                display: none;
            `;
            
            searchInput.parentElement.style.position = 'relative';
            searchInput.parentElement.appendChild(suggestionsContainer);
        };
        
        // Show suggestions
        const showSuggestions = (suggestions) => {
            createSuggestionsContainer();
            currentSuggestions = suggestions;
            
            if (suggestions.length === 0) {
                suggestionsContainer.style.display = 'none';
                return;
            }
            
            suggestionsContainer.innerHTML = '';
            
            suggestions.forEach(user => {
                const suggestionItem = document.createElement('div');
                suggestionItem.className = 'suggestion-item';
                suggestionItem.style.cssText = `
                    padding: 0.75rem;
                    cursor: pointer;
                    border-bottom: 1px solid var(--border-subtle);
                    display: flex;
                    align-items: center;
                    gap: 0.75rem;
                `;
                
                suggestionItem.innerHTML = `
                    <img src="${user.avatar_url || 'https://cdn.discordapp.com/embed/avatars/0.png'}" 
                         alt="Avatar" style="width: 32px; height: 32px; border-radius: 50%;">
                    <div>
                        <div style="font-weight: 600; color: var(--text-primary);">${user.username}#${user.discriminator}</div>
                        <div style="font-size: 0.875rem; color: var(--text-secondary);">ID: ${user.id}</div>
                    </div>
                `;
                
                suggestionItem.addEventListener('click', () => {
                    searchInput.value = user.username;
                    suggestionsContainer.style.display = 'none';
                    this.selectUser(user.id);
                });
                
                suggestionItem.addEventListener('mouseenter', () => {
                    suggestionItem.style.background = 'var(--surface-lighter)';
                });
                
                suggestionItem.addEventListener('mouseleave', () => {
                    suggestionItem.style.background = 'transparent';
                });
                
                suggestionsContainer.appendChild(suggestionItem);
            });
            
            suggestionsContainer.style.display = 'block';
        };
        
        // Hide suggestions
        const hideSuggestions = () => {
            if (suggestionsContainer) {
                suggestionsContainer.style.display = 'none';
            }
        };
        
        // Input event listener
        let searchTimeout;
        searchInput.addEventListener('input', (e) => {
            const query = e.target.value.trim();
            
            clearTimeout(searchTimeout);
            
            if (query.length < 2) {
                hideSuggestions();
                return;
            }
            
            searchTimeout = setTimeout(async () => {
                try {
                    const response = await this.apiCall(`/ticket-logs/search-users?query=${encodeURIComponent(query)}&guild_id=${this.currentGuild}`);
                    showSuggestions(response.users || []);
                } catch (error) {
                    console.error('Error getting suggestions:', error);
                    hideSuggestions();
                }
            }, 300);
        });
        
        // Hide suggestions when clicking outside
        document.addEventListener('click', (e) => {
            if (!searchInput.parentElement.contains(e.target)) {
                hideSuggestions();
            }
        });
        
        // Hide suggestions on focus out
        searchInput.addEventListener('blur', () => {
            setTimeout(hideSuggestions, 200);
        });
    }
    
    async loadSearchSuggestions() {
        if (!this.currentGuild) {
            return;
        }
        
        try {
            const response = await this.apiCall(`/ticket-logs/search-suggestions?guild_id=${this.currentGuild}`);
            const suggestions = response.suggestions || [];
            
            if (suggestions.length > 0) {
                this.displaySearchSuggestions(suggestions);
            }
        } catch (error) {
            console.error('Error loading search suggestions:', error);
        }
    }
    
    displaySearchSuggestions(suggestions) {
        const searchSection = document.querySelector('#ticket-logs .settings-section');
        if (!searchSection) return;
        
        // Remove existing suggestions if any
        const existingSuggestions = document.getElementById('searchSuggestions');
        if (existingSuggestions) {
            existingSuggestions.remove();
        }
        
        const suggestionsDiv = document.createElement('div');
        suggestionsDiv.id = 'searchSuggestions';
        suggestionsDiv.style.cssText = `
            margin-top: 1rem;
            padding: 1rem;
            background: var(--surface-dark);
            border-radius: 8px;
            border: 1px solid var(--border-subtle);
        `;
        
        suggestionsDiv.innerHTML = `
            <h5 style="margin: 0 0 0.75rem 0; color: var(--text-primary); font-size: 0.875rem;">
                <i class="fas fa-clock me-2"></i>Utilisateurs récents avec tickets
            </h5>
            <div class="suggestions-grid" style="display: grid; gap: 0.5rem;">
                ${suggestions.map(user => `
                    <div class="suggestion-chip" style="
                        padding: 0.5rem 0.75rem;
                        background: var(--surface-lighter);
                        border-radius: 6px;
                        cursor: pointer;
                        transition: var(--transition-fast);
                        display: flex;
                        align-items: center;
                        gap: 0.5rem;
                    " onclick="dashboard.selectUser('${user.id}')">
                        <img src="${user.avatar_url || 'https://cdn.discordapp.com/embed/avatars/0.png'}" 
                             alt="Avatar" style="width: 24px; height: 24px; border-radius: 50%;">
                        <span style="font-size: 0.875rem; color: var(--text-primary);">${user.username}</span>
                        <span style="font-size: 0.75rem; color: var(--text-secondary);">(${user.ticket_count} tickets)</span>
                    </div>
                `).join('')}
            </div>
        `;
        
        // Add hover effects
        const chips = suggestionsDiv.querySelectorAll('.suggestion-chip');
        chips.forEach(chip => {
            chip.addEventListener('mouseenter', () => {
                chip.style.background = 'var(--primary-yellow)';
                chip.style.color = 'var(--background-dark)';
            });
            
            chip.addEventListener('mouseleave', () => {
                chip.style.background = 'var(--surface-lighter)';
                chip.style.color = '';
            });
        });
        
        searchSection.appendChild(suggestionsDiv);
    }
    
    async debugTicketLogs() {
        if (!this.currentGuild) {
            return;
        }
        
        try {
            const response = await this.apiCall(`/ticket-logs/debug?guild_id=${this.currentGuild}`);
            console.log('🔍 Ticket Logs Debug Info:', response);
            
            if (response.google_drive_connected) {
                console.log(`✅ Google Drive connected`);
                console.log(`📊 Found ${response.total_logs} total logs`);
                console.log(`👥 ${response.unique_users} unique users`);
                console.log(`🎫 ${response.unique_tickets} unique tickets`);
                
                if (response.total_logs === 0) {
                    console.log('⚠️ No ticket logs found in Google Drive');
                    console.log('💡 Create and close some tickets to generate logs');
                }
            } else {
                console.log('❌ Google Drive connection failed');
                console.log('🔧 Check your Google Drive credentials');
            }
        } catch (error) {
            console.error('Debug ticket logs error:', error);
        }
    }

    async searchUser() {
        if (!this.currentGuild) {
            this.showError('Veuillez d\'abord sélectionner un serveur');
            return;
        }
        
        const searchInput = document.getElementById('userSearchInput');
        const query = searchInput.value.trim();
        
        if (!query) {
            this.showError('Veuillez entrer un nom d\'utilisateur ou un ID Discord');
            return;
        }
        
        try {
            this.showLoading('userResultsList', 'Recherche d\'utilisateurs...');
            
            const response = await this.apiCall(`/ticket-logs/search-users?query=${encodeURIComponent(query)}&guild_id=${this.currentGuild}`);
            
            if (response.users && response.users.length > 0) {
                this.displayUserResults(response.users);
                document.getElementById('userResultsSection').style.display = 'block';
            } else {
                document.getElementById('userResultsSection').style.display = 'none';
                this.showError('Aucun utilisateur trouvé');
            }
            
        } catch (error) {
            console.error('Error searching users:', error);
            this.showError('Erreur lors de la recherche d\'utilisateurs');
        }
    }

    displayUserResults(users) {
        const resultsList = document.getElementById('userResultsList');
        resultsList.innerHTML = '';
        
        users.forEach(user => {
            const userItem = document.createElement('div');
            userItem.className = 'user-item';
            userItem.innerHTML = `
                <img src="${user.avatar_url || 'https://cdn.discordapp.com/embed/avatars/0.png'}" 
                     alt="Avatar" class="user-avatar">
                <div class="user-info">
                    <div class="user-name">${user.username}#${user.discriminator}</div>
                    <div class="user-id">ID: ${user.id}</div>
                </div>
                <button class="user-select-btn" onclick="dashboard.selectUser('${user.id}')">
                    Sélectionner
                </button>
            `;
            resultsList.appendChild(userItem);
        });
    }

    async selectUser(userId) {
        if (!this.currentGuild) {
            this.showError('Veuillez d\'abord sélectionner un serveur');
            return;
        }
        
        try {
            this.showLoading('userTicketsList', 'Chargement des tickets...');
            
            const response = await this.apiCall(`/ticket-logs/user-tickets/${userId}?guild_id=${this.currentGuild}`);
            
            this.selectedUser = response.user;
            this.userTickets = response.tickets || [];
            
            this.displaySelectedUser();
            this.displayUserTickets();
            
            document.getElementById('userTicketsSection').style.display = 'block';
            
        } catch (error) {
            console.error('Error loading user tickets:', error);
            this.showError('Erreur lors du chargement des tickets');
        }
    }

    displaySelectedUser() {
        const userInfo = document.getElementById('selectedUserInfo');
        
        // Utiliser la même logique que les suggestions
        const username = this.selectedUser.discriminator && this.selectedUser.discriminator !== '0000' 
            ? `${this.selectedUser.username}#${this.selectedUser.discriminator}`
            : this.selectedUser.username;
        
        userInfo.innerHTML = `
            <img src="${this.selectedUser.avatar_url || 'https://cdn.discordapp.com/embed/avatars/0.png'}" 
                 alt="Avatar" class="user-avatar">
            <div class="user-info">
                <div class="user-name">${username}</div>
                <div class="user-id">ID: ${this.selectedUser.id}</div>
            </div>
        `;
    }

    displayUserTickets() {
        const ticketsList = document.getElementById('userTicketsList');
        const noTicketsState = document.getElementById('noTicketsState');
        
        if (this.userTickets.length === 0) {
            ticketsList.style.display = 'none';
            noTicketsState.style.display = 'block';
            return;
        }
        
        ticketsList.style.display = 'block';
        noTicketsState.style.display = 'none';
        ticketsList.innerHTML = '';
        
        this.userTickets.forEach((ticket, index) => {
            const ticketItem = document.createElement('div');
            ticketItem.className = 'ticket-item';
            
            const createdDate = new Date(ticket.created_at).toLocaleDateString('fr-FR');
            const createdTime = new Date(ticket.created_at).toLocaleTimeString('fr-FR', { 
                hour: '2-digit', 
                minute: '2-digit' 
            });
            const statusClass = ticket.status === 'open' ? 'open' : 'closed';
            const messageCount = ticket.message_count || 0;
            const eventCount = ticket.event_count || 0;
            
            // Formatage du nom d'utilisateur avec avatar Discord (même logique que les suggestions)
            let username = 'Utilisateur inconnu';
            let avatarUrl = 'https://cdn.discordapp.com/embed/avatars/0.png';
            
            // Utiliser la même logique que dans displaySearchSuggestions
            if (ticket.username && ticket.username !== 'Unknown' && ticket.username !== 'Inconnu') {
                username = ticket.discriminator && ticket.discriminator !== '0000' 
                    ? `${ticket.username}#${ticket.discriminator}`
                    : ticket.username;
                
                // Utiliser l'avatar Discord si disponible
                if (ticket.avatar_url) {
                    avatarUrl = ticket.avatar_url;
                }
            }
            
            ticketItem.innerHTML = `
                <div class="ticket-info">
                    <div class="ticket-header">
                        <div class="ticket-title">
                            <span class="ticket-name">Ticket ${index + 1}</span>
                            <span class="ticket-id-discrete">(${ticket.ticket_id})</span>
                        </div>
                        <span class="ticket-status ${statusClass}">${ticket.status === 'open' ? 'Ouvert' : 'Fermé'}</span>
                    </div>
                    <div class="ticket-meta">
                        <div class="ticket-user">
                            <img src="${avatarUrl}" alt="Avatar" class="user-avatar-small" onerror="this.src='https://cdn.discordapp.com/embed/avatars/0.png'">
                            <span>${username}</span>
                        </div>
                        <div class="ticket-stats">
                            <span class="message-count">💬 ${messageCount} message${messageCount > 1 ? 's' : ''}</span>
                            <span class="event-count">⚡ ${eventCount} événement${eventCount > 1 ? 's' : ''}</span>
                        </div>
                        <div class="ticket-date">📅 ${createdDate} à ${createdTime}</div>
                    </div>
                    <button class="ticket-view-btn" onclick="dashboard.viewTicketDetails('${ticket.file_id}')">
                        📋 Voir les détails
                    </button>
                </div>
            `;
            ticketsList.appendChild(ticketItem);
        });
    }

    async viewTicketDetails(fileId) {
        if (!this.currentGuild) {
            this.showError('Veuillez d\'abord sélectionner un serveur');
            return;
        }
        
        try {
            this.showLoading('ticketDetailsContent', 'Chargement des détails du ticket...');
            
            const response = await this.apiCall(`/ticket-logs/ticket-details/${fileId}?guild_id=${this.currentGuild}`);
            
            this.displayTicketDetails(response);
            
            // Show modal
            const modal = new bootstrap.Modal(document.getElementById('ticketDetailsModal'));
            modal.show();
            
        } catch (error) {
            console.error('Error loading ticket details:', error);
            this.showError('Erreur lors du chargement des détails du ticket');
        }
    }

    displayTicketDetails(ticketData) {
        const content = document.getElementById('ticketDetailsContent');
        const modalTitle = document.getElementById('ticketDetailsModalTitle');
        
        modalTitle.textContent = `Ticket #${ticketData.ticket_id}`;
        
        const createdDate = new Date(ticketData.created_at).toLocaleString('fr-FR');
        const statusClass = ticketData.status === 'open' ? 'open' : 'closed';
        const messageCount = ticketData.messages ? ticketData.messages.length : 0;
        const eventCount = ticketData.events ? ticketData.events.length : 0;
        
        // Formatage du nom d'utilisateur
        let username = 'Utilisateur inconnu';
        if (ticketData.username && ticketData.username !== 'Inconnu') {
            username = ticketData.discriminator && ticketData.discriminator !== '0000' 
                ? `${ticketData.username}#${ticketData.discriminator}`
                : ticketData.username;
        }
        
        let html = `
            <div class="ticket-header">
                <div class="ticket-title-section">
                    <h4 class="ticket-title">Ticket #${ticketData.ticket_id}</h4>
                    <div class="ticket-meta">
                        <div class="ticket-user-info">👤 ${username}</div>
                        <div class="ticket-stats">
                            <span class="message-count">💬 ${messageCount} message${messageCount > 1 ? 's' : ''}</span>
                            <span class="event-count">⚡ ${eventCount} événement${eventCount > 1 ? 's' : ''}</span>
                        </div>
                        <div class="ticket-dates">
                            <span>📅 Créé le: ${createdDate}</span>
                            <span class="ticket-status ${statusClass}">${ticketData.status === 'open' ? 'Ouvert' : 'Fermé'}</span>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        // Créer une liste combinée de messages et événements triés par timestamp
        const allItems = [];
        
        // Ajouter les messages
        if (ticketData.messages && ticketData.messages.length > 0) {
            ticketData.messages.forEach(message => {
                allItems.push({
                    type: 'message',
                    timestamp: message.timestamp,
                    data: message
                });
            });
        }
        
        // Ajouter les événements
        if (ticketData.events && ticketData.events.length > 0) {
            ticketData.events.forEach(event => {
                allItems.push({
                    type: 'event',
                    timestamp: event.timestamp,
                    data: event
                });
            });
        }
        
        // Trier par timestamp
        allItems.sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));
        
        if (allItems.length > 0) {
            html += '<div class="ticket-messages">';
            
            allItems.forEach((item, index) => {
                const itemDate = new Date(item.timestamp).toLocaleString('fr-FR');
                const itemTime = new Date(item.timestamp).toLocaleTimeString('fr-FR', { 
                    hour: '2-digit', 
                    minute: '2-digit' 
                });
                
                if (item.type === 'message') {
                    const message = item.data;
                    
                    // Formatage du nom d'auteur avec avatar
                    let authorName = message.author_name || 'Utilisateur inconnu';
                    let authorUsername = message.author_username || message.author_name || 'Inconnu';
                    let authorAvatar = 'https://cdn.discordapp.com/embed/avatars/0.png';
                    
                    if (message.author_discriminator && message.author_discriminator !== '0000') {
                        authorName = `${authorUsername}#${message.author_discriminator}`;
                    } else {
                        authorName = authorUsername;
                    }
                    
                    // Utiliser l'avatar Discord si disponible
                    if (message.author_avatar_url) {
                        authorAvatar = message.author_avatar_url;
                    } else if (message.author_id && message.author_id !== 'Inconnu') {
                        authorAvatar = `https://cdn.discordapp.com/avatars/${message.author_id}/${message.author_id}.png?size=64`;
                    }
                    
                    html += `
                        <div class="message-item">
                            <div class="message-header">
                                <div class="message-author-info">
                                    <img src="${authorAvatar}" alt="Avatar" class="message-avatar" onerror="this.src='https://cdn.discordapp.com/embed/avatars/0.png'">
                                    <div class="author-details">
                                        <span class="message-author">💬 ${authorName}</span>
                                        <span class="message-id">ID: ${message.author_id || 'Inconnu'}</span>
                                    </div>
                                </div>
                                <div class="message-time-info">
                                    <span class="message-date">${new Date(item.timestamp).toLocaleDateString('fr-FR')}</span>
                                    <span class="message-time">${itemTime}</span>
                                </div>
                            </div>
                            <div class="message-content">${message.content || '<em>Message vide</em>'}</div>
                        </div>
                    `;
                } else if (item.type === 'event') {
                    const event = item.data;
                    
                    // Mapper les champs d'événement
                    const eventType = event.type || event.event_type || 'Événement';
                    const eventDescription = event.details || event.description || 'Aucune description';
                    const eventUser = event.user_name || event.user || 'Utilisateur inconnu';
                    
                    // Traduire les types d'événements
                    const eventTypeTranslations = {
                        'created': 'Création',
                        'closed': 'Fermeture',
                        'reopened': 'Réouverture',
                        'deleted': 'Suppression'
                    };
                    const translatedEventType = eventTypeTranslations[eventType] || eventType;
                    
                    html += `
                        <div class="event-item">
                            <div class="event-header">
                                <div class="event-info">
                                    <span class="event-type">⚡ ${translatedEventType}</span>
                                    <span class="event-description">${eventDescription}</span>
                                    <span class="event-user">👤 ${eventUser}</span>
                                </div>
                                <div class="event-time-info">
                                    <span class="event-date">${new Date(item.timestamp).toLocaleDateString('fr-FR')}</span>
                                    <span class="event-time">${itemTime}</span>
                                </div>
                            </div>
                        </div>
                    `;
                }
            });
            
            html += '</div>';
        } else {
            html += '<div class="empty-state"><p>📭 Aucun message ou événement trouvé dans ce ticket</p></div>';
        }
        
        content.innerHTML = html;
    }

    showLoading(elementId, message = 'Chargement...') {
        const element = document.getElementById(elementId);
        if (element) {
            element.innerHTML = `
                <div style="text-align: center; padding: 2rem;">
                    <div class="loading-spinner"></div>
                    <p style="margin-top: 1rem; color: var(--text-secondary);">${message}</p>
                </div>
            `;
        }
    }

    showError(message) {
        // Create a simple toast notification
        const toast = document.createElement('div');
        toast.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: var(--error);
            color: white;
            padding: 1rem 1.5rem;
            border-radius: 8px;
            z-index: 9999;
            box-shadow: var(--shadow-lg);
        `;
        toast.textContent = message;
        
        document.body.appendChild(toast);
        
        setTimeout(() => {
            document.body.removeChild(toast);
        }, 5000);
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
                
                if (targetId === 'embed' && window.dashboard) {
                    console.log('🚀 Initializing embed creator...');
                    window.dashboard.initEmbedCreator().catch(error => {
                        console.error('Failed to initialize embed creator:', error);
                    });
                    window.dashboard.loadEmbedCreatorData().catch(error => {
                        console.error('Failed to load embed creator data:', error);
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

// Setup level-up customization event listeners
function setupLevelUpEventListeners() {
    console.log('🔧 Setting up level-up customization event listeners...');
    
    // Message type change listener
    const messageTypeSelect = document.getElementById('levelUpMessageType');
    if (messageTypeSelect) {
        messageTypeSelect.addEventListener('change', () => {
            if (window.dashboard) {
                window.dashboard.toggleLevelUpMessageType();
            }
        });
        console.log('✅ Message type change listener added');
    } else {
        console.warn('⚠️ Message type select not found');
    }
    
    // Intercept XP Settings Form submission
    const xpForm = document.getElementById('xpSettingsForm');
    if (xpForm) {
        xpForm.addEventListener('submit', (e) => {
            e.preventDefault();
            if (window.dashboard) {
                window.dashboard.saveXPSettings(e);
            }
        });
        console.log('✅ XP Settings Form submit listener added');
    } else {
        console.warn('⚠️ XP Settings Form not found');
    }
    
    // Welcome Settings Form
    const welcomeForm = document.getElementById('welcomeSettingsForm');
    if (welcomeForm) {
        welcomeForm.addEventListener('submit', (e) => {
            e.preventDefault();
            if (window.dashboard) {
                window.dashboard.saveWelcomeSettings(e);
            }
        });
        console.log('✅ Welcome Settings Form submit listener added');
    } else {
        console.warn('⚠️ Welcome Settings Form not found');
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
        { href: '#role-menus', target: 'role-menus' },
        { href: '#logs', target: 'logs' },
        { href: '#tickets', target: 'tickets' },
        { href: '#ticket-logs', target: 'ticket-logs' },
        { href: '#embed', target: 'embed' }
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

// ====================================
// Ticket Logs Configuration
// ====================================

let searchDebounceTimer = null;
let currentTicketDetails = null;

// Autocomplete suggestions
async function showSearchSuggestions() {
    const dashboard = window.dashboard;
    if (!dashboard || !dashboard.currentGuild) return;

    const searchInput = document.getElementById('ticketSearchInput');
    const searchValue = searchInput.value.trim();
    const suggestionsDiv = document.getElementById('searchSuggestions');
    
    if (searchValue.length < 2) {
        suggestionsDiv.style.display = 'none';
        return;
    }

    clearTimeout(searchDebounceTimer);
    searchDebounceTimer = setTimeout(async () => {
        try {
            const users = await dashboard.apiCall(`/guild/${dashboard.currentGuild}/members/search?query=${encodeURIComponent(searchValue)}`);
            
            if (!users || users.length === 0) {
                suggestionsDiv.style.display = 'none';
                return;
            }

            suggestionsDiv.innerHTML = '';
            
            for (const user of users) {
                // Get ticket count for this user
                const tickets = await dashboard.apiCall(`/guild/${dashboard.currentGuild}/tickets/user/${user.id}`);
                const ticketCount = tickets ? tickets.length : 0;
                
                if (ticketCount > 0) {
                    const suggestionItem = document.createElement('div');
                    suggestionItem.className = 'suggestion-item';
                    suggestionItem.innerHTML = `
                        <img class="suggestion-avatar" src="${user.avatar_url || '/static/default-avatar.png'}" alt="${user.username}">
                        <div class="suggestion-info">
                            <div class="suggestion-name">${user.username}</div>
                            <div class="suggestion-id">ID: ${user.id}</div>
                        </div>
                        <span class="suggestion-count">${ticketCount} ticket${ticketCount > 1 ? 's' : ''}</span>
                    `;
                    suggestionItem.addEventListener('click', () => {
                        searchInput.value = user.username;
                        suggestionsDiv.style.display = 'none';
                        searchTicketLogs();
                    });
                    suggestionsDiv.appendChild(suggestionItem);
                }
            }
            
            suggestionsDiv.style.display = suggestionsDiv.children.length > 0 ? 'block' : 'none';
        } catch (error) {
            console.error('Error fetching suggestions:', error);
        }
    }, 300);
}

// Close suggestions when clicking outside
document.addEventListener('click', function(e) {
    const searchInput = document.getElementById('ticketSearchInput');
    const suggestionsDiv = document.getElementById('searchSuggestions');
    if (searchInput && suggestionsDiv && !searchInput.contains(e.target) && !suggestionsDiv.contains(e.target)) {
        suggestionsDiv.style.display = 'none';
    }
});

async function searchTicketLogs() {
    const dashboard = window.dashboard;
    if (!dashboard || !dashboard.currentGuild) {
        dashboard.showError('Veuillez sélectionner un serveur');
        return;
    }

    const searchInput = document.getElementById('ticketSearchInput');
    const searchValue = searchInput.value.trim();
    
    if (!searchValue) {
        dashboard.showError('Veuillez entrer un nom d\'utilisateur ou un ID');
        return;
    }

    try {
        // Show loading state
        const ticketsList = document.getElementById('ticketsList');
        const resultsSection = document.getElementById('ticketSearchResults');
        const emptySection = document.getElementById('ticketSearchEmpty');
        
        resultsSection.style.display = 'block';
        emptySection.style.display = 'none';
        ticketsList.innerHTML = '<div class="loading-state"><i class="fas fa-spinner fa-spin me-2"></i>Recherche en cours...</div>';

        // Search for user first
        const users = await dashboard.apiCall(`/guild/${dashboard.currentGuild}/members/search?query=${encodeURIComponent(searchValue)}`);
        
        if (!users || users.length === 0) {
            emptySection.style.display = 'block';
            resultsSection.style.display = 'none';
            return;
        }

        // Get tickets for found users
        const userId = users[0].id;
        const tickets = await dashboard.apiCall(`/guild/${dashboard.currentGuild}/tickets/user/${userId}`);
        
        if (!tickets || tickets.length === 0) {
            emptySection.style.display = 'block';
            resultsSection.style.display = 'none';
            return;
        }

        // Update count
        document.getElementById('ticketResultsCount').textContent = `${tickets.length} ticket(s) trouvé(s)`;

        // Populate results
        ticketsList.innerHTML = '';
        tickets.forEach(ticket => {
            const ticketItem = createTicketItem(ticket);
            ticketsList.appendChild(ticketItem);
        });

    } catch (error) {
        console.error('Error searching tickets:', error);
        document.getElementById('ticketSearchEmpty').style.display = 'block';
        document.getElementById('ticketSearchResults').style.display = 'none';
    }
}

function createTicketItem(ticket) {
    const item = document.createElement('div');
    item.className = 'ticket-item';
    
    const statusClass = ticket.status === 'open' ? 'open' : 'closed';
    const statusText = ticket.status === 'open' ? 'Ouvert' : 'Fermé';
    
    const createdDate = new Date(ticket.created_at).toLocaleDateString('fr-FR', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric'
    });
    
    // Get avatar URL - use default if not available
    const avatarUrl = ticket.avatar_url || 'https://cdn.discordapp.com/embed/avatars/0.png';
    const username = ticket.username || ticket.display_name || 'Utilisateur inconnu';
    
    item.innerHTML = `
        <img src="${avatarUrl}" alt="${username}" class="ticket-avatar" onerror="this.src='https://cdn.discordapp.com/embed/avatars/0.png'">
        <div class="ticket-info">
            <div class="ticket-header">
                <div class="ticket-title">
                    <span class="ticket-username">${username}</span>
                    <span class="ticket-id-badge">#${ticket.channel_id}</span>
                </div>
                <span class="ticket-status ${statusClass}">${statusText}</span>
            </div>
            <div class="ticket-meta">
                <span class="ticket-date">
                    <i class="fas fa-calendar"></i> ${createdDate}
                </span>
                ${ticket.message_count ? `
                    <span class="message-count">
                        <i class="fas fa-comment"></i> ${ticket.message_count}
                    </span>
                ` : ''}
                ${ticket.event_count ? `
                    <span class="event-count">
                        <i class="fas fa-history"></i> ${ticket.event_count}
                    </span>
                ` : ''}
            </div>
        </div>
    `;
    
    // Add click handler to navigate to ticket details page
    item.style.cursor = 'pointer';
    item.addEventListener('click', () => {
        // Navigate to ticket details page
        const guildId = window.dashboard.currentGuild;
        window.location.href = `/dashboard/ticket/${guildId}/${ticket.file_id}`;
    });
    
    return item;
}

async function openTicketDetails(ticket) {
    const dashboard = window.dashboard;
    currentTicketDetails = ticket;
    
    // Get modal elements
    let modal = document.getElementById('ticketDetailsModal');
    if (!modal) {
        console.error('Modal element not found!');
        return;
    }
    
    // Use class instead of inline styles
    modal.classList.add('active');
    
    // Prevent body scroll when modal is open
    document.body.style.overflow = 'hidden';
    
    // Populate basic info
    document.getElementById('detailTicketId').textContent = `#${ticket.channel_id}`;
    
    const statusClass = ticket.status === 'open' ? 'open' : 'closed';
    const statusText = ticket.status === 'open' ? 'Ouvert' : 'Fermé';
    document.getElementById('detailTicketStatus').innerHTML = `<span class="ticket-status ${statusClass}">${statusText}</span>`;
    
    document.getElementById('detailTicketUser').textContent = ticket.username || 'Inconnu';
    document.getElementById('detailTicketCreated').textContent = new Date(ticket.created_at).toLocaleString('fr-FR');
    document.getElementById('detailTicketClosedBy').textContent = ticket.closed_by ? `ID: ${ticket.closed_by}` : 'N/A';
    document.getElementById('detailTicketClosed').textContent = ticket.closed_at ? new Date(ticket.closed_at).toLocaleString('fr-FR') : 'N/A';
    
    // Load transcript if available
    const transcriptPreview = document.getElementById('transcriptPreview');
    const transcriptSection = document.getElementById('ticketTranscriptSection');
    
    if (ticket.file_id) {
        transcriptPreview.innerHTML = '<div class="loading-state"><div class="spinner"></div><p>Chargement du transcript...</p></div>';
        
        try {
            // Load full transcript from API
            const transcriptData = await dashboard.apiCall(`/guild/${dashboard.currentGuild}/tickets/file/${ticket.file_id}`);
            
            if (transcriptData && transcriptData.messages && transcriptData.messages.length > 0) {
                // Display messages in a beautiful format
                let transcriptHTML = '<div class="transcript-messages">';
                
                transcriptData.messages.forEach(msg => {
                    const timestamp = new Date(msg.timestamp).toLocaleString('fr-FR', {
                        day: '2-digit',
                        month: '2-digit',
                        year: 'numeric',
                        hour: '2-digit',
                        minute: '2-digit'
                    });
                    
                    transcriptHTML += `
                        <div class="transcript-message">
                            <div class="message-header">
                                <div class="message-author">
                                    ${msg.author_avatar_url ? `<img src="${msg.author_avatar_url}" alt="${msg.author_name}" class="message-avatar">` : ''}
                                    <span class="message-author-name">${msg.author_name}</span>
                                </div>
                                <span class="message-timestamp">${timestamp}</span>
                            </div>
                            <div class="message-content">${escapeHtml(msg.content)}</div>
                            ${msg.attachments && msg.attachments.length > 0 ? `
                                <div class="message-attachments">
                                    ${msg.attachments.map(att => `
                                        <a href="${att.url}" target="_blank" class="attachment-link">
                                            <i class="fas fa-paperclip"></i> ${att.filename}
                                        </a>
                                    `).join('')}
                                </div>
                            ` : ''}
                        </div>
                    `;
                });
                
                transcriptHTML += '</div>';
                transcriptHTML += `<div class="transcript-footer">
                    <i class="fas fa-comment"></i> ${transcriptData.messages.length} message(s) au total
                </div>`;
                
                transcriptPreview.innerHTML = transcriptHTML;
            } else {
                transcriptPreview.innerHTML = '<p class="text-secondary">Aucun message dans ce transcript</p>';
            }
        } catch (error) {
            console.error('Error loading transcript:', error);
            transcriptPreview.innerHTML = '<p class="text-danger"><i class="fas fa-exclamation-triangle me-2"></i>Erreur lors du chargement du transcript</p>';
        }
    } else {
        transcriptPreview.innerHTML = '<p class="text-secondary">Aucun transcript disponible</p>';
    }
    
    // Load events timeline
    await loadTicketEvents(ticket);
    
    // Scroll modal content to top
    const modalBody = modal.querySelector('.ticket-modal-body');
    if (modalBody) {
        modalBody.scrollTop = 0;
    }
}

// Helper function to escape HTML
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

async function loadTicketEvents(ticket) {
    const dashboard = window.dashboard;
    const timeline = document.getElementById('ticketEventsTimeline');
    
    try {
        // Fetch events from API (you'll need to create this endpoint)
        const events = await dashboard.apiCall(`/guild/${dashboard.currentGuild}/tickets/${ticket.channel_id}/events`);
        
        if (!events || events.length === 0) {
            timeline.innerHTML = '<p class="text-secondary">Aucun événement enregistré</p>';
            return;
        }
        
        timeline.innerHTML = '';
        
        // Sort events by date (newest first)
        events.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
        
        events.forEach(event => {
            const eventItem = createTimelineItem(event);
            timeline.appendChild(eventItem);
        });
        
    } catch (error) {
        console.error('Error loading ticket events:', error);
        timeline.innerHTML = '<p class="text-secondary">Erreur lors du chargement des événements</p>';
    }
}

function createTimelineItem(event) {
    const item = document.createElement('div');
    item.className = 'timeline-item';
    
    const eventIcons = {
        'created': '🎫',
        'claimed': '🙋',
        'closed': '🔒',
        'deleted': '🗑️',
        'reopened': '🔓',
        'verified': '✅'
    };
    
    const eventTitles = {
        'created': 'Ticket créé',
        'claimed': 'Pris en charge',
        'closed': 'Fermé',
        'deleted': 'Supprimé',
        'reopened': 'Rouvert',
        'verified': 'Vérifié'
    };
    
    const timestamp = new Date(event.timestamp).toLocaleString('fr-FR', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
    
    item.innerHTML = `
        <div class="timeline-marker ${event.event_type}">
            ${eventIcons[event.event_type] || '📝'}
        </div>
        <div class="timeline-content">
            <div class="timeline-header">
                <span class="timeline-title">
                    ${eventIcons[event.event_type] || '📝'} ${eventTitles[event.event_type] || 'Événement'}
                </span>
                <span class="timeline-time">${timestamp}</span>
            </div>
            ${event.details ? `<div class="timeline-details">${event.details}</div>` : ''}
            ${event.user_name ? `
                <div class="timeline-user">
                    <span>Par: <strong>${event.user_name}</strong></span>
                </div>
            ` : ''}
        </div>
    `;
    
    return item;
}

function closeTicketDetailsModal() {
    const modal = document.getElementById('ticketDetailsModal');
    if (modal) {
        modal.classList.remove('active');
    }
    // Restore body scroll
    document.body.style.overflow = '';
    currentTicketDetails = null;
}

function openFullTranscript() {
    if (currentTicketDetails && currentTicketDetails.file_id) {
        window.open(`https://drive.google.com/file/d/${currentTicketDetails.file_id}/view`, '_blank');
    }
}

async function loadTicketLogsConfig() {
    const dashboard = window.dashboard;
    if (!dashboard || !dashboard.currentGuild) return;

    try {
        // Load server config to get ticket logs channels
        const config = await dashboard.apiCall(`/guild/${dashboard.currentGuild}/server-config`);
        
        // Populate channels dropdowns
        const ticketEventsLogChannel = document.getElementById('ticketEventsLogChannel');
        const ticketLogsChannel = document.getElementById('ticketLogsChannel');
        
        if (ticketEventsLogChannel && dashboard.channels) {
            // Clear and repopulate
            ticketEventsLogChannel.innerHTML = '<option value="">-- Désactivé --</option>';
            dashboard.channels.forEach(channel => {
                const option = document.createElement('option');
                option.value = channel.id;
                option.textContent = `#${channel.name}`;
                ticketEventsLogChannel.appendChild(option);
            });
            
            // Set current value
            if (config.ticket_events_log_channel_id) {
                ticketEventsLogChannel.value = config.ticket_events_log_channel_id;
            }
        }
        
        if (ticketLogsChannel && dashboard.channels) {
            // Clear and repopulate
            ticketLogsChannel.innerHTML = '<option value="">-- Non configuré --</option>';
            dashboard.channels.forEach(channel => {
                const option = document.createElement('option');
                option.value = channel.id;
                option.textContent = `#${channel.name}`;
                ticketLogsChannel.appendChild(option);
            });
            
            // Set current value
            if (config.ticket_logs_channel_id) {
                ticketLogsChannel.value = config.ticket_logs_channel_id;
            }
        }
        
    } catch (error) {
        console.error('Error loading ticket logs config:', error);
    }
}

async function saveTicketLogsConfig(e) {
    e.preventDefault();
    const dashboard = window.dashboard;
    if (!dashboard || !dashboard.currentGuild) return;

    const ticketEventsLogChannelId = document.getElementById('ticketEventsLogChannel').value;
    const ticketLogsChannelId = document.getElementById('ticketLogsChannel').value;

    try {
        const response = await dashboard.apiCall(`/guild/${dashboard.currentGuild}/server-config`, 'POST', {
            ticket_events_log_channel_id: ticketEventsLogChannelId || null,
            ticket_logs_channel_id: ticketLogsChannelId || null
        });

        if (response.success) {
            dashboard.showSuccess('Configuration des logs de tickets sauvegardée avec succès !');
        } else {
            dashboard.showError('Erreur lors de la sauvegarde de la configuration.');
        }
    } catch (error) {
        console.error('Error saving ticket logs config:', error);
        dashboard.showError('Erreur lors de la sauvegarde de la configuration.');
    }
}

// Initialize ticket logs configuration when tab is shown
document.addEventListener('DOMContentLoaded', function() {
    const ticketLogsForm = document.getElementById('ticketLogsConfigForm');
    if (ticketLogsForm) {
        ticketLogsForm.addEventListener('submit', saveTicketLogsConfig);
    }
    
    // Load recent tickets from Google Drive
    async function loadRecentTickets() {
        const dashboard = window.dashboard;
        if (!dashboard || !dashboard.currentGuild) {
            console.log('⚠️ No guild selected for recent tickets');
            return;
        }

        const loadingDiv = document.getElementById('recentTicketsLoading');
        const listDiv = document.getElementById('recentTicketsList');
        const emptyDiv = document.getElementById('recentTicketsEmpty');

        try {
            // Show loading
            loadingDiv.style.display = 'block';
            listDiv.style.display = 'none';
            emptyDiv.style.display = 'none';

            console.log(`📋 Loading recent tickets for guild ${dashboard.currentGuild}`);
            
            // Fetch recent tickets
            const tickets = await dashboard.apiCall(`/guild/${dashboard.currentGuild}/tickets/recent`);
            
            // Hide loading
            loadingDiv.style.display = 'none';
            
            if (!tickets || tickets.length === 0) {
                emptyDiv.style.display = 'block';
                return;
            }

            // Show tickets list
            listDiv.style.display = 'block';
            listDiv.innerHTML = '';
            
            tickets.forEach(ticket => {
                const ticketItem = createTicketItem(ticket);
                listDiv.appendChild(ticketItem);
            });

            console.log(`✅ Loaded ${tickets.length} recent tickets`);

        } catch (error) {
            console.error('❌ Error loading recent tickets:', error);
            loadingDiv.style.display = 'none';
            emptyDiv.style.display = 'block';
        }
    }
    
    // Add input listener for search suggestions
    const ticketSearchInput = document.getElementById('ticketSearchInput');
    if (ticketSearchInput) {
        ticketSearchInput.addEventListener('input', showSearchSuggestions);
        ticketSearchInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                document.getElementById('searchSuggestions').style.display = 'none';
                searchTicketLogs();
            }
        });
    }
    
    // Load config when switching to ticket-logs tab
    const ticketLogsLink = document.querySelector('a[href="#ticket-logs"]');
    if (ticketLogsLink) {
        ticketLogsLink.addEventListener('click', function() {
            setTimeout(() => {
                loadTicketLogsConfig();
                loadRecentTickets();
            }, 100);
        });
    }
});

// Initialize dashboard when DOM is ready
console.log('🔧 Setting up dashboard initialization...');
document.addEventListener('DOMContentLoaded', function() {
    console.log('📄 DOM Content Loaded, initializing dashboard...');
    window.dashboard = new Dashboard();
});
