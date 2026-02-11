#!/usr/bin/env python3
"""
Генерация диаграмм и графиков для GitHub Pages
"""

import json
from pathlib import Path
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import numpy as np

# Создаем директории
DATA_DIR = Path("data")
WEB_DIR = Path("web")
DIAGRAMS_DIR = DATA_DIR / "diagrams"
DIAGRAMS_DIR.mkdir(parents=True, exist_ok=True)
WEB_DIR.mkdir(exist_ok=True)

def generate_price_chart():
    """График цен по категориям"""
    prices_file = DATA_DIR / "prices.json"
    if not prices_file.exists():
        return
    
    with open(prices_file) as f:
        data = json.load(f)
    
    # Берем топ-5 запросов
    top_queries = list(data.keys())[:5]
    
    plt.figure(figsize=(12, 6))
    
    for query in top_queries:
        prices = data[query][-24:]  # Последние 24 часа
        hours = list(range(len(prices)))
        plt.plot(hours, prices, marker='o', label=query)
    
    plt.title('Динамика цен на Avito')
    plt.xlabel('Время (часы)')
    plt.ylabel('Цена (тыс ₽)')
    plt.legend()
    plt.grid(True)
    
    # Сохраняем
    chart_path = DIAGRAMS_DIR / f"price_chart_{datetime.now().strftime('%Y%m%d')}.png"
    plt.savefig(chart_path, dpi=100, bbox_inches='tight')
    plt.close()
    
    # Копируем в web директорию
    import shutil
    shutil.copy(chart_path, WEB_DIR / "price_chart.png")

def generate_category_pie():
    """Круговая диаграмма категорий"""
    categories = {
        'Электроника': 35,
        'Транспорт': 25,
        'Недвижимость': 20,
        'Работа': 12,
        'Услуги': 8
    }
    
    plt.figure(figsize=(10, 8))
    colors = ['#ff6b6b', '#4ecdc4', '#45b7d1', '#96ceb4', '#ffeaa5']
    
    plt.pie(categories.values(), 
            labels=categories.keys(),
            colors=colors,
            autopct='%1.1f%%',
            startangle=90)
    
    plt.title('Распределение категорий на Avito')
    
    pie_path = DIAGRAMS_DIR / f"category_pie_{datetime.now().strftime('%Y%m%d')}.png"
    plt.savefig(pie_path, dpi=100, bbox_inches='tight')
    plt.close()
    
    import shutil
    shutil.copy(pie_path, WEB_DIR / "category_pie.png")

def generate_trends_chart():
    """График популярных запросов"""
    trends_file = DATA_DIR / "trends.json"
    if not trends_file.exists():
        return
    
    with open(trends_file) as f:
        trends = json.load(f)
    
    queries = list(trends.keys())[:8]
    counts = [trends[q] for q in queries]
    
    plt.figure(figsize=(12, 6))
    plt.barh(queries, counts, color='#4ecdc4')
    plt.title('Топ-8 популярных запросов')
    plt.xlabel('Количество поисков')
    
    trends_path = DIAGRAMS_DIR / f"trends_{datetime.now().strftime('%Y%m%d')}.png"
    plt.savefig(trends_path, dpi=100, bbox_inches='tight')
    plt.close()
    
    import shutil
    shutil.copy(trends_path, WEB_DIR / "trends.png")

if __name__ == "__main__":
    print("📊 Generating diagrams...")
    generate_price_chart()
    generate_category_pie()
    generate_trends_chart()
    print("✅ Diagrams saved to web/")