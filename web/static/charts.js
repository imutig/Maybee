// Chart management functions for Maybee Dashboard
class ChartManager {
    constructor(dashboard) {
        this.dashboard = dashboard;
        this.memberGrowthChart = null;
        this.activityChart = null;
        this.xpDistributionChart = null;
        this.xpEvolutionChart = null;
        this.moderationChart = null;
    }

    // Load all charts
    loadCharts() {
        if (!this.dashboard.currentGuild) {
            console.log('❌ No guild selected, cannot load charts');
            return;
        }

        console.log('📊 Loading charts for guild:', this.dashboard.currentGuild);
        
        // Load all charts in parallel
        Promise.all([
            this.loadMemberGrowthChart(),
            this.loadActivityChart(),
            this.loadXPDistributionChart(),
            this.loadXPEvolutionChart(),
            this.loadModerationChart()
        ]).then(() => {
            console.log('✅ All charts loaded successfully');
        }).catch(error => {
            console.error('❌ Error loading charts:', error);
        });
    }

    // Load member growth chart
    loadMemberGrowthChart() {
        const canvas = document.getElementById('memberGrowthChart');
        const placeholder = document.getElementById('memberGrowthChartPlaceholder');
        const periodSelect = document.getElementById('memberGrowthPeriod');
        
        if (!canvas || !placeholder) return Promise.resolve();

        const period = periodSelect?.value || '7d';
        return this.dashboard.apiCall(`/guilds/${this.dashboard.currentGuild}/stats/member-growth?period=${period}`)
            .then(data => {
                // Check if we have data
                if (!data.has_data) {
                    // Show no data message
                    placeholder.innerHTML = `<div class="no-data-message">
                        <i class="fas fa-chart-line"></i>
                        <p>${data.message || 'Aucune donnée disponible'}</p>
                    </div>`;
                    placeholder.style.display = 'block';
                    canvas.style.display = 'none';
                    return;
                }
                
                // Hide placeholder and show canvas
                placeholder.style.display = 'none';
                canvas.style.display = 'block';
                
                // Destroy existing chart if it exists
                if (this.memberGrowthChart) {
                    this.memberGrowthChart.destroy();
                }
                
                // Create new chart
                const ctx = canvas.getContext('2d');
                this.memberGrowthChart = new Chart(ctx, {
                    type: 'line',
                    data: {
                        labels: data.labels || [],
                        datasets: [{
                            label: 'Membres',
                            data: data.data || [],
                            borderColor: '#4CAF50',
                            backgroundColor: 'rgba(76, 175, 80, 0.1)',
                            tension: 0,  // Straight lines between points
                            fill: true,
                            pointRadius: 4,
                            pointHoverRadius: 6
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: {
                                display: true,
                                position: 'top'
                            }
                        },
                        scales: {
                            y: {
                                beginAtZero: true,
                                ticks: {
                                    precision: 0
                                }
                            }
                        }
                    }
                });
                
                console.log('✅ Member growth chart loaded');
            })
            .catch(error => {
                console.error('❌ Error loading member growth chart:', error);
                placeholder.style.display = 'block';
                canvas.style.display = 'none';
            });
    }

    // Load activity chart
    loadActivityChart() {
        const canvas = document.getElementById('activityChart');
        const placeholder = document.getElementById('activityChartPlaceholder');
        const periodSelect = document.getElementById('activityPeriod');
        
        if (!canvas || !placeholder) return Promise.resolve();

        const period = periodSelect?.value || '24h';
        return this.dashboard.apiCall(`/guilds/${this.dashboard.currentGuild}/stats/activity?period=${period}`)
            .then(data => {
                // Check if we have data
                if (!data.has_data) {
                    // Show no data message
                    placeholder.innerHTML = `<div class="no-data-message">
                        <i class="fas fa-chart-bar"></i>
                        <p>${data.message || 'Aucune donnée disponible'}</p>
                    </div>`;
                    placeholder.style.display = 'block';
                    canvas.style.display = 'none';
                    return;
                }
                
                // Hide placeholder and show canvas
                placeholder.style.display = 'none';
                canvas.style.display = 'block';
                
                // Destroy existing chart if it exists
                if (this.activityChart) {
                    this.activityChart.destroy();
                }
                
                // Create new chart
                const ctx = canvas.getContext('2d');
                this.activityChart = new Chart(ctx, {
                    type: 'bar',
                    data: {
                        labels: data.labels || [],
                        datasets: [{
                            label: 'Messages',
                            data: data.data || [],
                            backgroundColor: '#2196F3',
                            borderColor: '#1976D2',
                            borderWidth: 1
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: {
                                display: true,
                                position: 'top'
                            }
                        },
                        scales: {
                            y: {
                                beginAtZero: true,
                                ticks: {
                                    precision: 0
                                }
                            }
                        }
                    }
                });
                
                console.log('✅ Activity chart loaded');
            })
            .catch(error => {
                console.error('❌ Error loading activity chart:', error);
                placeholder.style.display = 'block';
                canvas.style.display = 'none';
            });
    }

    // Load XP distribution chart
    loadXPDistributionChart() {
        const canvas = document.getElementById('xpDistributionChart');
        const placeholder = document.getElementById('xpDistributionChartPlaceholder');
        
        if (!canvas || !placeholder) return Promise.resolve();

        return this.dashboard.apiCall(`/guilds/${this.dashboard.currentGuild}/stats/xp-distribution`)
            .then(data => {
                // Check if we have data
                if (!data.has_data) {
                    // Show no data message
                    placeholder.innerHTML = `<div class="no-data-message">
                        <i class="fas fa-chart-pie"></i>
                        <p>${data.message || 'Aucune donnée disponible'}</p>
                    </div>`;
                    placeholder.style.display = 'block';
                    canvas.style.display = 'none';
                    return;
                }
                
                // Hide placeholder and show canvas
                placeholder.style.display = 'none';
                canvas.style.display = 'block';
                
                // Destroy existing chart if it exists
                if (this.xpDistributionChart) {
                    this.xpDistributionChart.destroy();
                }
                
                // Create new chart
                const ctx = canvas.getContext('2d');
                this.xpDistributionChart = new Chart(ctx, {
                    type: 'doughnut',
                    data: {
                        labels: data.labels || [],
                        datasets: [{
                            data: data.data || [],
                            backgroundColor: [
                                '#FF6384',
                                '#36A2EB',
                                '#FFCE56',
                                '#4BC0C0',
                                '#9966FF',
                                '#FF9F40'
                            ],
                            borderWidth: 2
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: {
                                display: true,
                                position: 'right'
                            }
                        }
                    }
                });
                
                console.log('✅ XP distribution chart loaded');
            })
            .catch(error => {
                console.error('❌ Error loading XP distribution chart:', error);
                placeholder.style.display = 'block';
                canvas.style.display = 'none';
            });
    }

    // Load XP evolution chart
    loadXPEvolutionChart() {
        const canvas = document.getElementById('xpEvolutionChart');
        const placeholder = document.getElementById('xpEvolutionChartPlaceholder');
        const periodSelect = document.getElementById('xpEvolutionPeriod');
        const typeSelect = document.getElementById('xpEvolutionType');
        
        if (!canvas || !placeholder) return Promise.resolve();

        const period = periodSelect?.value || '7d';
        const xpType = typeSelect?.value || 'both';
        return this.dashboard.apiCall(`/guilds/${this.dashboard.currentGuild}/stats/xp-evolution?period=${period}&xp_type=${xpType}`)
            .then(data => {
                // Check if we have data
                if (!data.has_data) {
                    // Show no data message
                    placeholder.innerHTML = `<div class="no-data-message">
                        <i class="fas fa-chart-line"></i>
                        <p>${data.message || 'Aucune donnée disponible'}</p>
                    </div>`;
                    placeholder.style.display = 'block';
                    canvas.style.display = 'none';
                    return;
                }
                
                // Hide placeholder and show canvas
                placeholder.style.display = 'none';
                canvas.style.display = 'block';
                
                // Destroy existing chart if it exists
                if (this.xpEvolutionChart) {
                    this.xpEvolutionChart.destroy();
                }
                
                // Create new chart
                const ctx = canvas.getContext('2d');
                this.xpEvolutionChart = new Chart(ctx, {
                    type: 'line',
                    data: {
                        labels: data.labels || [],
                    datasets: [{
                        label: 'Total XP Cumulé',
                        data: data.data || [],
                        borderColor: '#FFD700',
                        backgroundColor: 'rgba(255, 215, 0, 0.1)',
                        tension: 0,  // Straight lines between points
                        fill: true,
                        pointRadius: 4,
                        pointHoverRadius: 6
                    }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: {
                                display: true,
                                position: 'top'
                            }
                        },
                        scales: {
                            y: {
                                beginAtZero: true,
                                ticks: {
                                    precision: 0
                                }
                            }
                        }
                    }
                });
                
                console.log('✅ XP evolution chart loaded');
            })
            .catch(error => {
                console.error('❌ Error loading XP evolution chart:', error);
                placeholder.style.display = 'block';
                canvas.style.display = 'none';
            });
    }

    // Load moderation chart
    loadModerationChart() {
        const canvas = document.getElementById('moderationChart');
        const placeholder = document.getElementById('moderationChartPlaceholder');
        const periodSelect = document.getElementById('moderationPeriod');
        
        if (!canvas || !placeholder) return Promise.resolve();

        const period = periodSelect?.value || '7d';
        return this.dashboard.apiCall(`/guilds/${this.dashboard.currentGuild}/stats/moderation?period=${period}`)
            .then(data => {
                // Check if we have data
                if (!data.has_data) {
                    // Show no data message
                    placeholder.innerHTML = `<div class="no-data-message">
                        <i class="fas fa-shield-alt"></i>
                        <p>${data.message || 'Aucune donnée disponible'}</p>
                    </div>`;
                    placeholder.style.display = 'block';
                    canvas.style.display = 'none';
                    return;
                }
                
                // Hide placeholder and show canvas
                placeholder.style.display = 'none';
                canvas.style.display = 'block';
                
                // Destroy existing chart if it exists
                if (this.moderationChart) {
                    this.moderationChart.destroy();
                }
                
                // Create new chart
                const ctx = canvas.getContext('2d');
                this.moderationChart = new Chart(ctx, {
                    type: 'bar',
                    data: {
                        labels: data.labels || [],
                        datasets: [{
                            label: 'Actions de modération',
                            data: data.data || [],
                            backgroundColor: '#FF9800',
                            borderColor: '#F57C00',
                            borderWidth: 1
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: {
                                display: true,
                                position: 'top'
                            }
                        },
                        scales: {
                            y: {
                                beginAtZero: true,
                                ticks: {
                                    precision: 0
                                }
                            }
                        }
                    }
                });
                
                console.log('✅ Moderation chart loaded');
            })
            .catch(error => {
                console.error('❌ Error loading moderation chart:', error);
                placeholder.style.display = 'block';
                canvas.style.display = 'none';
            });
    }

    // Initialize chart event listeners
    initChartEventListeners() {
        // Member growth chart period change
        const memberGrowthPeriod = document.getElementById('memberGrowthPeriod');
        if (memberGrowthPeriod) {
            memberGrowthPeriod.addEventListener('change', () => {
                this.loadMemberGrowthChart();
            });
        }

        // Activity chart period change
        const activityPeriod = document.getElementById('activityPeriod');
        if (activityPeriod) {
            activityPeriod.addEventListener('change', () => {
                this.loadActivityChart();
            });
        }

        // XP distribution chart refresh
        const refreshXPChart = document.getElementById('refreshXPChart');
        if (refreshXPChart) {
            refreshXPChart.addEventListener('click', () => {
                this.loadXPDistributionChart();
            });
        }

        // XP evolution chart period change
        const xpEvolutionPeriod = document.getElementById('xpEvolutionPeriod');
        if (xpEvolutionPeriod) {
            xpEvolutionPeriod.addEventListener('change', () => {
                this.loadXPEvolutionChart();
            });
        }

        // XP evolution chart type change
        const xpEvolutionType = document.getElementById('xpEvolutionType');
        if (xpEvolutionType) {
            xpEvolutionType.addEventListener('change', () => {
                this.loadXPEvolutionChart();
            });
        }

        // Moderation chart period change
        const moderationPeriod = document.getElementById('moderationPeriod');
        if (moderationPeriod) {
            moderationPeriod.addEventListener('change', () => {
                this.loadModerationChart();
            });
        }
    }

    // Clear all charts
    clearCharts() {
        const charts = [
            this.memberGrowthChart,
            this.activityChart,
            this.xpDistributionChart,
            this.xpEvolutionChart,
            this.moderationChart
        ];

        charts.forEach(chart => {
            if (chart) {
                chart.destroy();
            }
        });

        // Reset chart variables
        this.memberGrowthChart = null;
        this.activityChart = null;
        this.xpDistributionChart = null;
        this.xpEvolutionChart = null;
        this.moderationChart = null;

        // Show placeholders
        const placeholders = [
            'memberGrowthChartPlaceholder',
            'activityChartPlaceholder',
            'xpDistributionChartPlaceholder',
            'xpEvolutionChartPlaceholder',
            'moderationChartPlaceholder'
        ];

        placeholders.forEach(id => {
            const placeholder = document.getElementById(id);
            if (placeholder) {
                placeholder.style.display = 'block';
            }
        });

        // Hide canvases
        const canvases = [
            'memberGrowthChart',
            'activityChart',
            'xpDistributionChart',
            'xpEvolutionChart',
            'moderationChart'
        ];

        canvases.forEach(id => {
            const canvas = document.getElementById(id);
            if (canvas) {
                canvas.style.display = 'none';
            }
        });
    }
};
