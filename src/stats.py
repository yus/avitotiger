#!/usr/bin/env python3
"""
Avito Statistics Generator - Запускается каждый час
Генерирует статистику для GitHub Pages
"""

import json
from pathlib import Path
from datetime import datetime, timedelta
from collections import Counter
import numpy as np

BASE_DIR = Path(__file__).parent.parent.parent
DATA_DIR = BASE_DIR / 'data'
WEB_DIR = BASE_DIR / 'web'

DATA_DIR.mkdir(exist_ok=True)
WEB_DIR.mkdir(exist_ok=True)

def load_json(file: Path):
    """Загрузить JSON"""
    if file.exists():
        try:
            return json.loads(file.read_text(encoding='utf-8'))
        except:
            return {}
    return {}

def generate_daily_stats():
    """Генерация ежедневной статистики"""
    print("📊 Generating daily statistics...")
    
    # Загружаем данные
    prices = load_json(DATA_DIR / 'prices.json')
    trends = load_json(DATA_DIR / 'trends.json')
    seen = load_json(DATA_DIR / 'seen_ads.json')
    
    # Сегодняшняя дата
    today = datetime.now().strftime('%Y-%m-%d')
    
    # Статистика
    stats = {
        'date': today,
        'total_searches': sum(trends.values()) if trends else 0,
        'new_ads': len(seen.get('ads', [])) if seen else 0,
        'avg_price': 0,
        'top_queries': [],
        'categories': {}
    }
    
    # Средняя цена
    all_prices = []
    for query, data in prices.items():
        if data:
            prices_list = [p['price'] for p in data[-24:]]  # Последние 24 часа
            if prices_list:
                all_prices.extend(prices_list)
    
    if all_prices:
        stats['avg_price'] = int(np.mean(all_prices))
    
    # Топ запросов
    if trends:
        top = sorted(trends.items(), key=lambda x: x[1], reverse=True)[:10]
        stats['top_queries'] = [{'query': q, 'count': c} for q, c in top]
    
    # Сохраняем
    stats_file = WEB_DIR / 'stats.json'
    stats_file.write_text(json.dumps(stats, indent=2), encoding='utf-8')
    
    # Сохраняем для веб-дашборда
    web_stats = {
        'totalSearches': stats['total_searches'],
        'newAds': stats['new_ads'],
        'avgPrice': stats['avg_price'],
        'topQuery': stats['top_queries'][0]['query'] if stats['top_queries'] else '—',
        'lastUpdate': datetime.now().isoformat()
    }
    
    web_stats_file = WEB_DIR / 'dashboard_stats.json'
    web_stats_file.write_text(json.dumps(web_stats), encoding='utf-8')
    
    print(f"✅ Statistics saved to {WEB_DIR}")
    return stats

def generate_weekly_report():
    """Генерация недельного отчета"""
    print("📈 Generating weekly report...")
    
    weekly_file = DATA_DIR / 'weekly_report.json'
    
    report = {
        'week': datetime.now().strftime('%W'),
        'year': datetime.now().year,
        'generated_at': datetime.now().isoformat(),
        'total_searches': 0,
        'avg_daily_searches': 0,
        'top_queries_week': []
    }
    
    weekly_file.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(f"✅ Weekly report saved")

if __name__ == "__main__":
    generate_daily_stats()
    generate_weekly_report()
