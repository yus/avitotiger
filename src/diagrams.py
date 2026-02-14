#!/usr/bin/env python3
"""
Generate price charts and diagrams for GitHub Pages
"""

import json
from pathlib import Path
from datetime import datetime
import matplotlib.pyplot as plt

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / 'data'
WEB_DIR = BASE_DIR / 'web'
DIAGRAMS_DIR = DATA_DIR / 'diagrams'

DIAGRAMS_DIR.mkdir(parents=True, exist_ok=True)

def load_json(file_path):
    if file_path.exists():
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def generate_price_chart():
    """Generate price chart from prices.json (flattening dict values)"""
    prices = load_json(DATA_DIR / 'prices.json')
    
    plt.figure(figsize=(12, 6))
    
    top_queries = list(prices.keys())[:5]
    
    for query in top_queries:
        data = prices.get(query, [])
        if data:
            # Extract just the price numbers from the list of dicts
            values = [item['price'] / 1000 for item in data[-24:]]  # Last 24 points, in thousand rubles
            hours = list(range(len(values)))
            plt.plot(hours, values, marker='o', label=query, linewidth=2)
    
    plt.title(f'Price Trends on Avito - {datetime.now().strftime("%Y-%m-%d")}')
    plt.xlabel('Time (hours ago)')
    plt.ylabel('Price (thousand ₽)')
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    chart_path = DIAGRAMS_DIR / f"price_chart_{datetime.now().strftime('%Y%m%d')}.png"
    plt.savefig(chart_path, dpi=100, bbox_inches='tight')
    plt.close()
    
    # Copy to web directory
    import shutil
    shutil.copy(chart_path, WEB_DIR / "price_chart.png")
    print(f"✅ Price chart saved")

def generate_category_pie():
    """Generate category distribution pie chart"""
    categories = {'Electronics': 35, 'Transport': 25, 'Realty': 20, 'Jobs': 12, 'Services': 8}
    
    plt.figure(figsize=(10, 8))
    plt.pie(categories.values(), labels=categories.keys(), autopct='%1.1f%%', startangle=90)
    plt.title('Avito Category Distribution')
    
    pie_path = DIAGRAMS_DIR / f"category_pie_{datetime.now().strftime('%Y%m%d')}.png"
    plt.savefig(pie_path, dpi=100, bbox_inches='tight')
    plt.close()
    
    import shutil
    shutil.copy(pie_path, WEB_DIR / "category_pie.png")
    print(f"✅ Category pie saved")

def generate_trends_chart():
    """Generate trends bar chart"""
    trends = load_json(DATA_DIR / 'trends.json')
    
    if trends:
        top = sorted(trends.items(), key=lambda x: x[1], reverse=True)[:8]
        queries = [q for q, _ in top]
        counts = [c for _, c in top]
        
        plt.figure(figsize=(12, 6))
        plt.barh(queries, counts, color='#4ecdc4')
        plt.title('Top 8 Search Queries')
        plt.xlabel('Search count')
        
        trends_path = DIAGRAMS_DIR / f"trends_{datetime.now().strftime('%Y%m%d')}.png"
        plt.savefig(trends_path, dpi=100, bbox_inches='tight')
        plt.close()
        
        import shutil
        shutil.copy(trends_path, WEB_DIR / "trends.png")
        print(f"✅ Trends chart saved")

if __name__ == "__main__":
    print("📊 Generating diagrams...")
    generate_price_chart()
    generate_category_pie()
    generate_trends_chart()
    print("✅ All diagrams saved")
