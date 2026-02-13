// Add to your dashboard HTML
async function loadSearchHistory() {
    try {
        // Fetch last 10 searches from data/searches/
        const response = await fetch('/data/searches/latest.json');
        const searches = await response.json();
        
        // Group by query for trending
        const trends = {};
        searches.forEach(s => {
            trends[s.query] = (trends[s.query] || 0) + 1;
        });
        
        // Sort by popularity
        const trending = Object.entries(trends)
            .sort((a,b) => b[1] - a[1])
            .slice(0, 5);
        
        // Update dashboard
        const container = document.getElementById('trending-searches');
        if (container) {
            container.innerHTML = trending.map(([q, count]) => 
                `<li>🔍 ${q} <span class="count">${count}</span></li>`
            ).join('');
        }
        
        // Update "Searches today" counter
        const today = new Date().toISOString().split('T')[0];
        const todaySearches = searches.filter(s => 
            s.timestamp.startsWith(today)
        ).length;
        
        const todayEl = document.getElementById('searches-today');
        if (todayEl) todayEl.textContent = todaySearches;
        
    } catch (e) {
        console.log('No search history yet');
    }
}

// Call on dashboard load
document.addEventListener('DOMContentLoaded', loadSearchHistory);
