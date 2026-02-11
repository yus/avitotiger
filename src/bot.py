#!/usr/bin/env python3
"""
Avito Tiger Bot for GitHub Actions
Проверяет новые объявления и отправляет уведомления в Telegram
Запускается по CRON каждые 30 минут
"""

import os
import sys
import json
import asyncio
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
import logging

# Добавляем корень проекта в PATH
sys.path.insert(0, str(Path(__file__).parent.parent))

from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import TelegramError
import aiohttp
from bs4 import BeautifulSoup
from fake_useragent import UserAgent

# ===================== КОНФИГУРАЦИЯ =====================

# Токен бота из GitHub Secrets
TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
ADMIN_IDS = os.getenv('TELEGRAM_ADMIN_IDS', '').split(',')

# Пути к файлам
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / 'data'
DB_FILE = DATA_DIR / 'db.json'
LOG_DIR = BASE_DIR / 'logs'
LOG_FILE = LOG_DIR / 'bot.log'

# Создаем директории
DATA_DIR.mkdir(exist_ok=True)
LOG_DIR.mkdir(exist_ok=True)

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('AvitoTiger')

# ===================== БАЗА ДАННЫХ =====================

class Database:
    """JSON база данных для GitHub Actions"""
    
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.data = self._load()
    
    def _load(self) -> Dict:
        """Загрузить базу данных"""
        if self.db_path.exists():
            try:
                with open(self.db_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return self._default()
        return self._default()
    
    def _default(self) -> Dict:
        """Структура БД по умолчанию"""
        return {
            "users": {},        # Пользователи
            "searches": {},     # Поисковые запросы
            "seen_ads": [],     # ID просмотренных объявлений
            "stats": {          # Статистика
                "total_checks": 0,
                "total_new_ads": 0,
                "last_check": None
            }
        }
    
    def save(self):
        """Сохранить базу данных"""
        with open(self.db_path, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)
    
    def get_searches(self) -> Dict:
        """Получить все активные поиски"""
        return self.data.get("searches", {})
    
    def add_search(self, user_id: int, query: str, **kwargs) -> str:
        """Добавить поисковый запрос"""
        search_id = f"{user_id}_{datetime.now().timestamp()}"
        self.data["searches"][search_id] = {
            "user_id": user_id,
            "query": query,
            "created_at": datetime.now().isoformat(),
            "last_check": None,
            "active": True,
            **kwargs
        }
        self.save()
        return search_id
    
    def delete_search(self, search_id: str) -> bool:
        """Удалить поиск"""
        if search_id in self.data["searches"]:
            self.data["searches"][search_id]["active"] = False
            self.save()
            return True
        return False
    
    def is_ad_seen(self, ad_id: str) -> bool:
        """Проверяли ли уже объявление"""
        return ad_id in self.data["seen_ads"]
    
    def mark_ad_seen(self, ad_id: str):
        """Отметить объявление как просмотренное"""
        if ad_id not in self.data["seen_ads"]:
            self.data["seen_ads"].append(ad_id)
            # Храним только последние 1000 объявлений
            if len(self.data["seen_ads"]) > 1000:
                self.data["seen_ads"] = self.data["seen_ads"][-1000:]
            self.save()
    
    def update_stats(self, new_ads: int = 0):
        """Обновить статистику"""
        self.data["stats"]["total_checks"] += 1
        self.data["stats"]["total_new_ads"] += new_ads
        self.data["stats"]["last_check"] = datetime.now().isoformat()
        self.save()

# ===================== ПАРСЕР AVITO =====================

class AvitoParser:
    """Парсер объявлений Avito"""
    
    BASE_URL = "https://www.avito.ru"
    
    def __init__(self):
        self.ua = UserAgent()
        self.session = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, *args):
        await self.session.close()
    
    def _get_headers(self) -> Dict:
        """Рандомный User-Agent"""
        return {
            'User-Agent': self.ua.random,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
    
    async def search(self, query: str, max_results: int = 5) -> List[Dict]:
        """Поиск объявлений"""
        try:
            headers = self._get_headers()
            params = {
                'q': query,
                's': '1'  # Сортировка по дате (новые сверху)
            }
            
            # Добавляем задержку
            await asyncio.sleep(random.uniform(1, 3))
            
            async with self.session.get(
                f"{self.BASE_URL}/rossiya",
                params=params,
                headers=headers,
                timeout=30
            ) as response:
                if response.status == 200:
                    html = await response.text()
                    return self._parse_results(html, max_results)
                else:
                    logger.error(f"HTTP {response.status} for query '{query}'")
                    return []
        except asyncio.TimeoutError:
            logger.error(f"Timeout for query '{query}'")
            return []
        except Exception as e:
            logger.error(f"Error searching '{query}': {e}")
            return []
    
    def _parse_results(self, html: str, max_results: int) -> List[Dict]:
        """Парсинг HTML результатов"""
        soup = BeautifulSoup(html, 'html.parser')
        ads = []
        
        # Ищем объявления
        items = soup.select('[data-marker="item"]')
        
        for item in items[:max_results]:
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
                if price_elem:
                    price = price_elem.get('content', '0')
                else:
                    price = "0"
                
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
                    'title': title[:100],  # Обрезаем длинные заголовки
                    'price': price,
                    'url': url,
                    'date': date,
                    'location': location,
                    'found_at': datetime.now().isoformat()
                })
                
            except Exception as e:
                logger.error(f"Error parsing ad: {e}")
                continue
        
        return ads

# ===================== ФОРМАТТЕРЫ =====================

def format_price(price_str: str) -> str:
    """Форматирование цены"""
    try:
        price = int(float(price_str))
        if price >= 1_000_000:
            return f"{price/1_000_000:.1f} млн ₽"
        elif price >= 1_000:
            return f"{price/1_000:.0f} тыс ₽"
        else:
            return f"{price} ₽"
    except:
        return "Цена не указана"

def format_ad_message(ad: Dict, query: str) -> str:
    """Форматирование сообщения об объявлении"""
    message = f"🆕 **Новое объявление!**\n\n"
    message += f"🔍 **Запрос:** {query}\n"
    message += f"🏷 **{ad['title']}**\n"
    message += f"💰 **Цена:** {format_price(ad['price'])}\n"
    
    if ad['location']:
        message += f"📍 **Место:** {ad['location']}\n"
    if ad['date']:
        message += f"🕐 **Опубликовано:** {ad['date']}\n"
    
    message += f"🔗 [Открыть объявление]({ad['url']})\n"
    message += f"\n⏱ Найдено: {datetime.now().strftime('%H:%M:%S')}"
    
    return message

# ===================== ОСНОВНАЯ ЛОГИКА =====================

async def send_telegram_message(bot: Bot, chat_id: int, text: str, keyboard=None):
    """Отправка сообщения в Telegram"""
    try:
        await bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode='Markdown',
            disable_web_page_preview=False,
            reply_markup=keyboard
        )
        return True
    except TelegramError as e:
        logger.error(f"Failed to send message to {chat_id}: {e}")
        return False

async def check_searches(db: Database, bot: Bot):
    """Проверить все активные поиски"""
    searches = db.get_searches()
    total_new = 0
    
    if not searches:
        logger.info("No active searches")
        return 0
    
    for search_id, search_data in searches.items():
        if not search_data.get('active', True):
            continue
        
        user_id = search_data['user_id']
        query = search_data['query']
        
        logger.info(f"🔍 Checking '{query}' for user {user_id}")
        
        # Парсим Avito
        async with AvitoParser() as parser:
            ads = await parser.search(query, max_results=5)
        
        # Проверяем новые объявления
        new_ads = 0
        for ad in ads:
            if not db.is_ad_seen(ad['id']):
                db.mark_ad_seen(ad['id'])
                new_ads += 1
                total_new += 1
                
                # Отправляем уведомление
                message = format_ad_message(ad, query)
                
                # Кнопки
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("📱 Открыть", url=ad['url'])],
                    [InlineKeyboardButton("🗑 Удалить поиск", callback_data=f"delete_{search_id}")]
                ])
                
                await send_telegram_message(bot, user_id, message, keyboard)
                logger.info(f"✅ New ad sent: {ad['title'][:30]}...")
                
                # Задержка между сообщениями
                await asyncio.sleep(0.5)
        
        # Обновляем время последней проверки
        db.data["searches"][search_id]["last_check"] = datetime.now().isoformat()
        db.save()
        
        logger.info(f"📊 Found {new_ads} new ads for '{query}'")
    
    return total_new

async def main():
    """Главная функция"""
    start_time = datetime.now()
    logger.info("=" * 60)
    logger.info(f"🚀 Avito Tiger Bot started at {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Проверка токена
    if not TOKEN:
        logger.error("❌ TELEGRAM_BOT_TOKEN not set in environment variables!")
        return
    
    # Инициализация
    db = Database(DB_FILE)
    bot = Bot(token=TOKEN)
    
    try:
        # Проверяем соединение с Telegram
        me = await bot.get_me()
        logger.info(f"✅ Bot authorized: @{me.username}")
        
        # Отправляем уведомление админам о запуске
        for admin_id in ADMIN_IDS:
            if admin_id:
                await send_telegram_message(
                    bot, 
                    int(admin_id),
                    f"🟢 Бот запущен\n⏱ {start_time.strftime('%H:%M:%S')}"
                )
        
        # Проверяем все поиски
        new_ads_total = await check_searches(db, bot)
        
        # Обновляем статистику
        db.update_stats(new_ads_total)
        
        # Итоговый отчет
        elapsed = (datetime.now() - start_time).total_seconds()
        logger.info(f"📊 Total new ads: {new_ads_total}")
        logger.info(f"⏱ Execution time: {elapsed:.2f}s")
        logger.info(f"🏁 Bot finished at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
    except Exception as e:
        logger.exception(f"❌ Fatal error: {e}")
        
        # Уведомляем админов об ошибке
        for admin_id in ADMIN_IDS:
            if admin_id:
                await send_telegram_message(
                    bot,
                    int(admin_id),
                    f"❌ **Ошибка бота**\n```\n{str(e)[:200]}...\n```"
                )

if __name__ == "__main__":
    asyncio.run(main())
