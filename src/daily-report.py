#!/usr/bin/env python3
"""
Daily Report Generator - Запускается каждый день в 23:00 MSK
Отправляет подробный отчет в Telegram и сохраняет статистику
"""

import os
import sys
import json
import asyncio
from pathlib import Path
from datetime import datetime, timedelta
from collections import Counter
import matplotlib
matplotlib.use('Agg')  # Без GUI
import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))

from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup

# ===================== КОНФИГ =====================

TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
ADMIN_IDS = list(map(int, os.getenv('TELEGRAM_ADMIN_IDS', '').split(','))) if os.getenv('TELEGRAM_ADMIN_IDS') else []

BASE_DIR = Path(__file__).parent.parent.parent
DATA_DIR = BASE_DIR / 'data'
REPORTS_DIR = DATA_DIR / 'daily_reports'
DIAGRAMS_DIR = DATA_DIR / 'diagrams'

REPORTS_DIR.mkdir(parents=True, exist_ok=True)
DIAGRAMS_DIR.mkdir(parents=True, exist_ok=True)

# ===================== ЗАГРУЗКА ДАННЫХ =====================

def load_json(file_path):
    """Загрузить JSON файл"""
    if file_path.exists():
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_json(file_path, data):
    """Сохранить JSON файл"""
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

# ===================== ГЕНЕРАЦИЯ ОТЧЕТА =====================

def generate_daily_report():
    """Сгенерировать отчет за день"""
    today = datetime.now().strftime('%Y-%m-%d')
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    
    # Загружаем данные
    trends = load_json(DATA_DIR / 'trends.json')
    prices = load_json(DATA_DIR / 'prices.json')
    seen_ads = load_json(DATA_DIR / 'seen_ads.json')
    
    # Топ запросов
    top_queries = []
    if trends:
        sorted_trends = sorted(trends.items(), key=lambda x: x[1], reverse=True)
        top_queries = sorted_trends[:10]
    
    # Изменения цен
    price_changes = []
    for query, data in prices.items():
        if len(data) >= 2:
            yesterday_price = data[-2].get('price', 0)
            today_price = data[-1].get('price', 0)
            if yesterday_price > 0:
                change = ((today_price - yesterday_price) / yesterday_price) * 100
                price_changes.append({
                    'query': query,
                    'yesterday': yesterday_price,
                    'today': today_price,
                    'change': round(change, 1)
                })
    
    price_changes.sort(key=lambda x: abs(x['change']), reverse=True)
    
    # Количество новых объявлений
    new_ads_today = 0
    if seen_ads and 'ads' in seen_ads:
        new_ads_today = len(seen_ads['ads'][-50:])
    
    # Средняя цена
    all_prices = []
    for query, data in prices.items():
        if data:
            prices_list = [p['price'] for p in data[-24:]]
            all_prices.extend(prices_list)
    
    avg_price = int(np.mean(all_prices)) if all_prices else 0
    
    # Формируем отчет
    report = {
        'date': today,
        'generated_at': datetime.now().isoformat(),
        'total_searches': sum(trends.values()) if trends else 0,
        'new_ads_today': new_ads_today,
        'top_queries': top_queries[:10],
        'price_changes': price_changes[:5],
        'avg_price': avg_price,
        'total_queries_count': len(trends) if trends else 0
    }
    
    # Сохраняем отчет
    report_file = REPORTS_DIR / f"report_{today}.json"
    save_json(report_file, report)
    
    return report

def generate_price_chart(report_date):
    """Сгенерировать график цен для отчета"""
    prices = load_json(DATA_DIR / 'prices.json')
    
    plt.figure(figsize=(12, 6))
    
    # Берем топ-5 запросов
    top_queries = list(prices.keys())[:5]
    
    for query in top_queries:
        data = prices.get(query, [])
        if data:
            values = [p['price'] / 1000 for p in data[-24:]]  # в тыс руб
            hours = list(range(len(values)))
            plt.plot(hours, values, marker='o', label=query, linewidth=2)
    
    plt.title(f'Динамика цен на Avito - {report_date}', fontsize=14, pad=20)
    plt.xlabel('Время (часы)', fontsize=12)
    plt.ylabel('Цена (тыс ₽)', fontsize=12)
    plt.legend(loc='best')
    plt.grid(True, alpha=0.3)
    
    chart_path = DIAGRAMS_DIR / f"daily_chart_{report_date}.png"
    plt.savefig(chart_path, dpi=100, bbox_inches='tight')
    plt.close()
    
    return chart_path

# ===================== ОТПРАВКА В TELEGRAM =====================

async def send_daily_report(bot, report, chart_path):
    """Отправить отчет в Telegram"""
    
    # Формируем текст отчета
    text = f"📊 **Ежедневный отчет Avito**\n"
    text += f"📅 {report['date']}\n\n"
    
    text += f"🔍 **Всего поисков:** {report['total_searches']:,}\n"
    text += f"🆕 **Новых объявлений:** {report['new_ads_today']}\n"
    text += f"💰 **Средняя цена:** {report['avg_price']:,} ₽\n\n"
    
    if report['top_queries']:
        text += f"🔥 **Топ-5 запросов дня:**\n"
        for i, (query, count) in enumerate(report['top_queries'][:5], 1):
            text += f"{i}. {query} — {count} раз\n"
        text += "\n"
    
    if report['price_changes']:
        text += f"📈 **Изменение цен:**\n"
        for item in report['price_changes'][:3]:
            emoji = "📈" if item['change'] > 0 else "📉"
            text += f"{emoji} {item['query']}: {item['change']}% "
            text += f"({item['yesterday']:,} → {item['today']:,} ₽)\n"
    
    text += f"\n📊 Полная статистика: https://yus.github.io/avitotiger/"
    
    # Кнопки
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Веб-дашборд", url="https://yus.github.io/avitotiger/")],
        [InlineKeyboardButton("🔍 Поиск на Avito", switch_inline_query_current_chat="")]
    ])
    
    # Отправляем график
    for admin_id in ADMIN_IDS:
        try:
            with open(chart_path, 'rb') as f:
                await bot.send_photo(
                    chat_id=admin_id,
                    photo=f,
                    caption=text[:1024],
                    parse_mode='Markdown'
                )
            
            # Отправляем полный текст отдельно если нужно
            if len(text) > 1024:
                await bot.send_message(
                    chat_id=admin_id,
                    text=text,
                    parse_mode='Markdown',
                    reply_markup=keyboard,
                    disable_web_page_preview=True
                )
            
            print(f"✅ Daily report sent to {admin_id}")
            
        except Exception as e:
            print(f"❌ Failed to send to {admin_id}: {e}")

# ===================== ОСНОВНОЕ =====================

async def main():
    """Главная функция"""
    print(f"📅 Generating daily report for {datetime.now().strftime('%Y-%m-%d')}")
    
    if not TOKEN:
        print("❌ No token!")
        return
    
    # Генерируем отчет
    report = generate_daily_report()
    print(f"✅ Report generated")
    
    # Генерируем график
    chart_path = generate_price_chart(report['date'])
    print(f"✅ Chart generated")
    
    # Отправляем в Telegram
    bot = Bot(token=TOKEN)
    await send_daily_report(bot, report, chart_path)
    
    # Сохраняем в веб-директорию для дашборда
    web_dir = BASE_DIR / 'web'
    web_dir.mkdir(exist_ok=True)
    
    web_stats = {
        'date': report['date'],
        'totalSearches': report['total_searches'],
        'newAds': report['new_ads_today'],
        'avgPrice': report['avg_price'],
        'topQuery': report['top_queries'][0][0] if report['top_queries'] else '—',
        'lastUpdate': datetime.now().isoformat()
    }
    
    stats_file = web_dir / 'dashboard_stats.json'
    save_json(stats_file, web_stats)
    
    print(f"✅ Daily report completed at {datetime.now().strftime('%H:%M:%S')}")

if __name__ == "__main__":
    asyncio.run(main())