// Moderation History Management
class ModerationHistory {
    constructor(dashboard) {
        this.dashboard = dashboard;
        this.currentPage = 1;
        this.totalPages = 1;
        this.filters = {
            user: '',
            action: '',
            date: '',
            limit: 25
        };
    }
    
    async init() {
        console.log('🐝 Initializing moderation history...');
        this.setupEventListeners();
        await this.loadHistory();
        await this.loadStats();
    }
    
    setupEventListeners() {
        // Refresh button
        const refreshBtn = document.getElementById('refreshHistoryBtn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => {
                this.loadHistory();
                this.loadStats();
            });
        }
        
        // Export button
        const exportBtn = document.getElementById('exportHistoryBtn');
        if (exportBtn) {
            exportBtn.addEventListener('click', () => {
                this.exportHistory();
            });
        }
        
        // Apply filters button
        const applyFiltersBtn = document.getElementById('applyHistoryFiltersBtn');
        if (applyFiltersBtn) {
            applyFiltersBtn.addEventListener('click', () => {
                this.applyFilters();
            });
        }
        
        // Clear filters button
        const clearFiltersBtn = document.getElementById('clearHistoryFiltersBtn');
        if (clearFiltersBtn) {
            clearFiltersBtn.addEventListener('click', () => {
                this.clearFilters();
            });
        }
        
        // Pagination buttons
        const prevBtn = document.getElementById('prevPageBtn');
        const nextBtn = document.getElementById('nextPageBtn');
        
        if (prevBtn) {
            prevBtn.addEventListener('click', () => {
                if (this.currentPage > 1) {
                    this.currentPage--;
                    this.loadHistory();
                }
            });
        }
        
        if (nextBtn) {
            nextBtn.addEventListener('click', () => {
                if (this.currentPage < this.totalPages) {
                    this.currentPage++;
                    this.loadHistory();
                }
            });
        }
    }
    
    async loadHistory() {
        try {
            const guildId = this.dashboard.guildId;
            const offset = (this.currentPage - 1) * this.filters.limit;
            
            const params = new URLSearchParams({
                limit: this.filters.limit,
                offset: offset
            });
            
            if (this.filters.user) {
                params.append('user_id', this.filters.user);
            }
            if (this.filters.action) {
                params.append('action_type', this.filters.action);
            }
            if (this.filters.date) {
                params.append('date_filter', this.filters.date);
            }
            
            const response = await fetch(`/api/moderation/history/${guildId}?${params}`);
            const data = await response.json();
            
            if (data.success) {
                this.displayHistory(data.data);
                this.updatePagination(data.pagination);
            } else {
                console.error('Failed to load moderation history:', data.error);
                this.showError(data.error);
            }
        } catch (error) {
            console.error('Error loading moderation history:', error);
            this.showError('Failed to load moderation history');
        }
    }
    
    async loadStats() {
        try {
            const guildId = this.dashboard.guildId;
            const response = await fetch(`/api/moderation/stats/${guildId}`);
            const data = await response.json();
            
            if (data.success) {
                this.displayStats(data.data.totals);
            } else {
                console.error('Failed to load moderation stats:', data.error);
            }
        } catch (error) {
            console.error('Error loading moderation stats:', error);
        }
    }
    
    displayHistory(history) {
        const tbody = document.getElementById('moderationHistoryTable');
        if (!tbody) return;
        
        if (history.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="6" class="no-data" data-translate="moderation.no_history_found">No moderation history found</td>
                </tr>
            `;
            return;
        }
        
        tbody.innerHTML = history.map(entry => {
            const userDisplay = entry.user_name ? 
                `${entry.user_name}#${entry.user_discriminator}` : 
                `User ${entry.user_id}`;
            
            const moderatorDisplay = entry.moderator_name ? 
                `${entry.moderator_name}#${entry.moderator_discriminator}` : 
                `Moderator ${entry.moderator_id}`;
            
            const actionEmoji = this.getActionEmoji(entry.action_type);
            const durationText = entry.duration_minutes ? 
                this.formatDuration(entry.duration_minutes) : '-';
            
            const timestamp = new Date(entry.timestamp);
            const dateStr = timestamp.toLocaleDateString();
            const timeStr = timestamp.toLocaleTimeString();
            
            return `
                <tr>
                    <td>
                        <div class="user-info">
                            <span class="user-name">${this.escapeHtml(userDisplay)}</span>
                            <span class="user-id">${entry.user_id}</span>
                        </div>
                    </td>
                    <td>
                        <span class="action-badge action-${entry.action_type}">
                            ${actionEmoji} ${entry.action_type.toUpperCase()}
                        </span>
                    </td>
                    <td>
                        <div class="moderator-info">
                            <span class="moderator-name">${this.escapeHtml(moderatorDisplay)}</span>
                        </div>
                    </td>
                    <td>
                        <span class="reason-text" title="${this.escapeHtml(entry.reason || '')}">
                            ${this.escapeHtml(entry.reason || 'No reason provided')}
                        </span>
                    </td>
                    <td>
                        <div class="date-info">
                            <span class="date">${dateStr}</span>
                            <span class="time">${timeStr}</span>
                        </div>
                    </td>
                    <td>
                        <span class="duration">${durationText}</span>
                    </td>
                </tr>
            `;
        }).join('');
    }
    
    displayStats(stats) {
        const totalActionsEl = document.getElementById('totalActions');
        const uniqueUsersEl = document.getElementById('uniqueUsers');
        const activeModeratorsEl = document.getElementById('activeModerators');
        
        if (totalActionsEl) totalActionsEl.textContent = stats.total_actions || 0;
        if (uniqueUsersEl) uniqueUsersEl.textContent = stats.unique_users || 0;
        if (activeModeratorsEl) activeModeratorsEl.textContent = stats.unique_moderators || 0;
    }
    
    updatePagination(pagination) {
        this.totalPages = Math.ceil(pagination.total / pagination.limit);
        
        const prevBtn = document.getElementById('prevPageBtn');
        const nextBtn = document.getElementById('nextPageBtn');
        const paginationInfo = document.getElementById('paginationInfo');
        const paginationContainer = document.getElementById('moderationPagination');
        
        if (prevBtn) {
            prevBtn.disabled = this.currentPage <= 1;
        }
        
        if (nextBtn) {
            nextBtn.disabled = this.currentPage >= this.totalPages;
        }
        
        if (paginationInfo) {
            paginationInfo.textContent = `Page ${this.currentPage} of ${this.totalPages}`;
        }
        
        if (paginationContainer) {
            paginationContainer.style.display = this.totalPages > 1 ? 'flex' : 'none';
        }
    }
    
    applyFilters() {
        const userFilter = document.getElementById('historyUserFilter');
        const actionFilter = document.getElementById('historyActionFilter');
        const dateFilter = document.getElementById('historyDateFilter');
        const limitFilter = document.getElementById('historyLimitFilter');
        
        this.filters.user = userFilter ? userFilter.value.trim() : '';
        this.filters.action = actionFilter ? actionFilter.value : '';
        this.filters.date = dateFilter ? dateFilter.value : '';
        this.filters.limit = limitFilter ? parseInt(limitFilter.value) : 25;
        
        this.currentPage = 1;
        this.loadHistory();
    }
    
    clearFilters() {
        const userFilter = document.getElementById('historyUserFilter');
        const actionFilter = document.getElementById('historyActionFilter');
        const dateFilter = document.getElementById('historyDateFilter');
        const limitFilter = document.getElementById('historyLimitFilter');
        
        if (userFilter) userFilter.value = '';
        if (actionFilter) actionFilter.value = '';
        if (dateFilter) dateFilter.value = '';
        if (limitFilter) limitFilter.value = '25';
        
        this.filters = {
            user: '',
            action: '',
            date: '',
            limit: 25
        };
        
        this.currentPage = 1;
        this.loadHistory();
    }
    
    async exportHistory() {
        try {
            const guildId = this.dashboard.guildId;
            const params = new URLSearchParams();
            
            if (this.filters.user) {
                params.append('user_id', this.filters.user);
            }
            if (this.filters.action) {
                params.append('action_type', this.filters.action);
            }
            if (this.filters.date) {
                params.append('date_filter', this.filters.date);
            }
            
            const response = await fetch(`/api/moderation/export/${guildId}?${params}`, {
                method: 'POST'
            });
            const data = await response.json();
            
            if (data.success) {
                // Download CSV file
                const blob = new Blob([data.data.csv_content], { type: 'text/csv' });
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = data.data.filename;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                window.URL.revokeObjectURL(url);
            } else {
                console.error('Failed to export moderation history:', data.error);
                alert('Failed to export moderation history: ' + data.error);
            }
        } catch (error) {
            console.error('Error exporting moderation history:', error);
            alert('Failed to export moderation history');
        }
    }
    
    getActionEmoji(actionType) {
        const emojis = {
            'warn': '⚠️',
            'timeout': '⏰',
            'kick': '👢',
            'ban': '🔨',
            'unban': '✅',
            'unmute': '🔊'
        };
        return emojis[actionType] || '❓';
    }
    
    formatDuration(minutes) {
        if (minutes < 60) {
            return `${minutes}m`;
        } else if (minutes < 1440) {
            const hours = Math.floor(minutes / 60);
            const remainingMinutes = minutes % 60;
            return remainingMinutes > 0 ? `${hours}h${remainingMinutes}m` : `${hours}h`;
        } else {
            const days = Math.floor(minutes / 1440);
            const remainingHours = Math.floor((minutes % 1440) / 60);
            return remainingHours > 0 ? `${days}d${remainingHours}h` : `${days}d`;
        }
    }
    
    showError(message) {
        const tbody = document.getElementById('moderationHistoryTable');
        if (tbody) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="6" class="no-data error">
                        <i class="fas fa-exclamation-triangle"></i>
                        ${this.escapeHtml(message)}
                    </td>
                </tr>
            `;
        }
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Initialize moderation history when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    // Wait for dashboard to be initialized
    setTimeout(() => {
        if (window.dashboard) {
            window.moderationHistory = new ModerationHistory(window.dashboard);
            
            // Initialize when moderation tab is shown
            const moderationTab = document.querySelector('[data-tab="moderation"]');
            if (moderationTab) {
                moderationTab.addEventListener('click', () => {
                    setTimeout(() => {
                        if (window.moderationHistory) {
                            window.moderationHistory.init();
                        }
                    }, 100);
                });
            }
        }
    }, 1000);
});
