#!/usr/bin/env python3
"""
Avito Parser - Запускается каждые 30 минут
Сохраняет данные в JSON и отправляет уведомления
"""

import os
import sys
import json
import asyncio
import random
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

import aiohttp
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup

# ===================== КОНФИГ =====================

TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
ADMIN_IDS = list(map(int, os.getenv('TELEGRAM_ADMIN_IDS', '').split(','))) if os.getenv('TELEGRAM_ADMIN_IDS') else []

BASE_DIR = Path(__file__).parent.parent.parent
DATA_DIR = BASE_DIR / 'data'
DATA_DIR.mkdir(exist_ok=True)

PRICES_FILE = DATA_DIR / 'prices.json'
TRENDS_FILE = DATA_DIR / 'trends.json'
SEEN_ADS_FILE = DATA_DIR / 'seen_ads.json'

# ===================== ПАРСЕР =====================

class AvitoParser:
    """Парсер Avito с антиблокировкой"""
    
    BASE_URL = "https://www.avito.ru"
    
    def __init__(self):
        self.ua = UserAgent()
    
    def _get_headers(self):
        """Реальные заголовки браузера"""
        return {
            'User-Agent': self.ua.random,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
        }
    
    async def search(self, query: str, limit: int = 10) -> List[Dict]:
        """Поиск объявлений"""
        async with aiohttp.ClientSession() as session:
            try:
                await asyncio.sleep(random.uniform(2, 4))
                
                headers = self._get_headers()
                params = {'q': query}
                
                async with session.get(
                    f"{self.BASE_URL}/rossiya",
                    params=params,
                    headers=headers,
                    timeout=30
                ) as response:
                    
                    if response.status != 200:
                        print(f"❌ HTTP {response.status} for {query}")
                        return []
                    
                    html = await response.text()
                    return self._parse_results(html, limit)
                    
            except Exception as e:
                print(f"❌ Error: {e}")
                return []
    
    def _parse_results(self, html: str, limit: int) -> List[Dict]:
        """Парсинг HTML"""
        soup = BeautifulSoup(html, 'html.parser')
        ads = []
        
        items = soup.select('[data-marker="item"]')
        
        for item in items[:limit]:
            try:
                # ID объявления
                ad_id = item.get('id', '')
                if not ad_id:
                    continue
                
                # Заголовок
                title_elem = item.select_one('[itemprop="name"]')
                title = title_elem.text.strip() if title_elem else "Без названия"
                
                # Цена
                price_elem = item.select_one('[itemprop="price"]')
                price = price_elem.get('content', '0') if price_elem else '0'
                
                # Ссылка
                link_elem = item.select_one('a[href*="/"]')
                if link_elem:
                    href = link_elem.get('href', '')
                    url = f"{self.BASE_URL}{href}" if href.startswith('/') else href
                else:
                    url = ""
                
                # Дата
                date_elem = item.select_one('[data-marker="item-date"]')
                date = date_elem.text.strip() if date_elem else ""
                
                # Местоположение
                location_elem = item.select_one('[class*="address"]')
                location = location_elem.text.strip() if location_elem else ""
                
                ads.append({
                    'id': ad_id,
                    'title': title[:100],
                    'price': price,
                    'url': url,
                    'date': date,
                    'location': location,
                    'query': query,
                    'found_at': datetime.now().isoformat()
                })
                
            except Exception as e:
                print(f"❌ Parse error: {e}")
                continue
        
        return ads

# ===================== БАЗА ДАННЫХ =====================

def load_json(file: Path, default: dict = None):
    """Загрузить JSON"""
    if default is None:
        default = {}
    if file.exists():
        try:
            return json.loads(file.read_text(encoding='utf-8'))
        except:
            return default
    return default

def save_json(file: Path, data: dict):
    """Сохранить JSON"""
    file.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')

# ===================== СТАТИСТИКА =====================

def update_prices(query: str, price: float):
    """Обновить историю цен"""
    prices = load_json(PRICES_FILE, {})
    
    if query not in prices:
        prices[query] = []
    
    prices[query].append({
        'price': price,
        'time': datetime.now().isoformat()
    })
    
    # Храним только последние 100 значений
    if len(prices[query]) > 100:
        prices[query] = prices[query][-100:]
    
    save_json(PRICES_FILE, prices)

def update_trends(query: str):
    """Обновить тренды запросов"""
    trends = load_json(TRENDS_FILE, {})
    
    if query not in trends:
        trends[query] = 0
    
    trends[query] += 1
    
    # Сортируем по популярности
    trends = dict(sorted(trends.items(), key=lambda x: x[1], reverse=True))
    
    save_json(TRENDS_FILE, trends)

# ===================== УВЕДОМЛЕНИЯ =====================

async def send_notification(bot: Bot, user_id: int, ad: Dict):
    """Отправить уведомление о новом объявлении"""
    try:
        price = int(float(ad['price'])) if ad['price'].replace('.', '').isdigit() else 0
        if price >= 1000:
            price_text = f"{price/1000:.0f} тыс ₽"
        else:
            price_text = f"{price} ₽"
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔗 Открыть объявление", url=ad['url'])]
        ])
        
        text = (
            f"🆕 **Новое объявление!**\n\n"
            f"🔍 **Запрос:** {ad['query']}\n"
            f"🏷 **{ad['title']}**\n"
            f"💰 **Цена:** {price_text}\n"
        )
        
        if ad['location']:
            text += f"📍 **Место:** {ad['location']}\n"
        
        await bot.send_message(
            chat_id=user_id,
            text=text,
            parse_mode='Markdown',
            reply_markup=keyboard,
            disable_web_page_preview=False
        )
        return True
    except Exception as e:
        print(f"❌ Send error: {e}")
        return False

# ===================== ОСНОВНОЕ =====================

async def main():
    """Главная функция"""
    print(f"🚀 Parser started at {datetime.now()}")
    
    if not TOKEN:
        print("❌ No token!")
        return
    
    bot = Bot(token=TOKEN)
    parser = AvitoParser()
    
    # Загружаем просмотренные объявления
    seen_ads = load_json(SEEN_ADS_FILE, {"ads": []})
    
    # Топ-5 запросов для проверки
    trends = load_json(TRENDS_FILE, {})
    top_queries = list(trends.keys())[:5] if trends else ["iphone 13", "macbook", "ps5", "велосипед", "диван"]
    
    print(f"🔍 Checking {len(top_queries)} queries...")
    
    new_ads_count = 0
    
    for query in top_queries:
        print(f"  📍 Searching: {query}")
        
        ads = await parser.search(query, limit=3)
        
        for ad in ads:
            if ad['id'] not in seen_ads['ads']:
                seen_ads['ads'].append(ad['id'])
                new_ads_count += 1
                
                # Отправляем уведомления админам
                for admin_id in ADMIN_IDS:
                    await send_notification(bot, admin_id, ad)
                
                # Обновляем статистику цен
                try:
                    price_val = float(ad['price'])
                    update_prices(query, price_val)
                except:
                    pass
                
                await asyncio.sleep(0.5)
        
        await asyncio.sleep(random.uniform(1, 3))
    
    # Обновляем тренды
    for query in top_queries:
        update_trends(query)
    
    # Сохраняем просмотренные (храним последние 1000)
    seen_ads['ads'] = seen_ads['ads'][-1000:]
    save_json(SEEN_ADS_FILE, seen_ads)
    
    print(f"✅ Found {new_ads_count} new ads")
    print(f"🏁 Parser finished at {datetime.now()}")

if __name__ == "__main__":
    asyncio.run(main())
