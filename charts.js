// Avito Tiger Dashboard Charts
// Автообновление графиков каждые 5 минут

class AvitoCharts {
    constructor() {
        this.charts = {};
        this.init();
    }

    async init() {
        await this.loadData();
        this.renderPriceChart();
        this.renderCategoryChart();
        this.renderTrendsChart();
        this.startAutoRefresh();
    }

    async loadData() {
        try {
            // Загружаем статистику
            const statsResponse = await fetch('dashboard_stats.json');
            this.stats = await statsResponse.json();
            
            // Обновляем цифры
            this.updateStats();
            
            // Загружаем историю цен
            const pricesResponse = await fetch('../data/prices.json');
            this.prices = await pricesResponse.json();
            
            // Загружаем тренды
            const trendsResponse = await fetch('../data/trends.json');
            this.trends = await trendsResponse.json();
            
        } catch (error) {
            console.log('Waiting for data...', error);
        }
    }

    updateStats() {
        if (!this.stats) return;
        
        document.getElementById('totalSearches').innerHTML = 
            this.stats.totalSearches?.toLocaleString() || '0';
        document.getElementById('newAds').innerHTML = 
            this.stats.newAds?.toLocaleString() || '0';
        document.getElementById('avgPrice').innerHTML = 
            this.stats.avgPrice ? `${this.stats.avgPrice.toLocaleString()} ₽` : '0 ₽';
        document.getElementById('topQuery').innerHTML = 
            this.stats.topQuery || '—';
    }

    renderPriceChart() {
        const ctx = document.getElementById('priceChart')?.getContext('2d');
        if (!ctx) return;

        // Если уже есть график, уничтожаем
        if (this.charts.price) {
            this.charts.price.destroy();
        }

        // Подготавливаем данные
        const labels = [];
        const datasets = [];

        if (this.prices) {
            const topQueries = Object.keys(this.prices).slice(0, 3);
            
            topQueries.forEach((query, index) => {
                const data = this.prices[query]?.slice(-24).map(p => p.price) || [];
                const colors = ['#667eea', '#764ba2', '#48bb78'];
                
                datasets.push({
                    label: query,
                    data: data,
                    borderColor: colors[index],
                    backgroundColor: colors[index] + '20',
                    tension: 0.4,
                    fill: false
                });
            });

            // Последние 24 часа
            for (let i = 0; i < 24; i++) {
                const hour = new Date();
                hour.setHours(hour.getHours() - (23 - i));
                labels.push(hour.getHours() + ':00');
            }
        }

        this.charts.price = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: datasets
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: 'Динамика цен (последние 24 часа)'
                    },
                    legend: {
                        position: 'bottom'
                    }
                },
                scales: {
                    y: {
                        beginAtZero: false,
                        ticks: {
                            callback: function(value) {
                                return value.toLocaleString() + ' ₽';
                            }
                        }
                    }
                }
            }
        });
    }

    renderCategoryChart() {
        const ctx = document.getElementById('categoryChart')?.getContext('2d');
        if (!ctx) return;

        if (this.charts.category) {
            this.charts.category.destroy();
        }

        // Примерные данные категорий
        const categories = {
            'Электроника': 35,
            'Транспорт': 25,
            'Недвижимость': 20,
            'Работа': 12,
            'Услуги': 8
        };

        this.charts.category = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: Object.keys(categories),
                datasets: [{
                    data: Object.values(categories),
                    backgroundColor: ['#667eea', '#764ba2', '#48bb78', '#f6ad55', '#fc8181'],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: 'Распределение категорий'
                    },
                    legend: {
                        position: 'bottom'
                    }
                }
            }
        });
    }

    renderTrendsChart() {
        const ctx = document.getElementById('trendsChart')?.getContext('2d');
        if (!ctx) return;

        if (this.charts.trends) {
            this.charts.trends.destroy();
        }

        const queries = [];
        const counts = [];

        if (this.trends) {
            const topTrends = Object.entries(this.trends)
                .sort((a, b) => b[1] - a[1])
                .slice(0, 8);

            topTrends.forEach(([query, count]) => {
                queries.push(query.length > 15 ? query.slice(0, 12) + '...' : query);
                counts.push(count);
            });
        }

        this.charts.trends = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: queries,
                datasets: [{
                    label: 'Количество поисков',
                    data: counts,
                    backgroundColor: '#4ecdc4',
                    borderRadius: 5
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: 'Топ-8 популярных запросов'
                    },
                    legend: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            stepSize: 1
                        }
                    }
                }
            }
        });
    }

    startAutoRefresh() {
        // Обновляем данные каждые 5 минут
        setInterval(async () => {
            console.log('🔄 Refreshing charts...');
            await this.loadData();
            this.renderPriceChart();
            this.renderTrendsChart();
            document.getElementById('updateTime').innerHTML = 
                `🕐 Последнее обновление: ${new Date().toLocaleString('ru-RU')}`;
        }, 300000);
    }
}

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', () => {
    window.avitoCharts = new AvitoCharts();
});