#!/usr/bin/env python3
"""
Avito Tiger Bot
"""

import os
import sys
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from telegram.error import TelegramError
import aiohttp
from bs4 import BeautifulSoup
from fake_useragent import UserAgent

TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

# ===================== ПАРСЕР =====================

class AvitoParser:
    def __init__(self):
        self.ua = UserAgent()
    
    async def search(self, query: str, limit: int = 5):
        async with aiohttp.ClientSession() as session:
            headers = {'User-Agent': self.ua.random}
            params = {'q': query}
            
            try:
                async with session.get(
                    "https://www.avito.ru/rossiya",
                    params=params,
                    headers=headers,
                    timeout=30
                ) as response:
                    if response.status != 200:
                        return []
                    
                    html = await response.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    ads = []
                    
                    for item in soup.select('[data-marker="item"]')[:limit]:
                        try:
                            title = item.select_one('[itemprop="name"]')
                            price = item.select_one('[itemprop="price"]')
                            link = item.select_one('a[href*="/"]')
                            location = item.select_one('[class*="address"]')
                            
                            ads.append({
                                'title': title.text.strip() if title else 'Без названия',
                                'price': price.get('content', '0') if price else '0',
                                'url': f"https://www.avito.ru{link.get('href')}" if link else '',
                                'location': location.text.strip() if location else ''
                            })
                        except:
                            continue
                    return ads
            except:
                return []

# ===================== КОМАНДЫ =====================

async def send_typing_action(update: Update):
    """Отправить действие 'печатает...'"""
    try:
        if update.message:
            await update.message.chat.send_action(action='typing')
        elif update.callback_query:
            await update.callback_query.message.chat.send_action(action='typing')
    except:
        pass

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start"""
    await update.message.reply_text(
        "🤖 **Avito Tiger Bot**\n\n"
        "🔍 **Поиск объявлений:**\n"
        "`/search iphone 13`\n\n"
        "📊 **Статистика:**\n"
        "`/stats iphone` - график цен\n"
        "`/top` - популярные запросы\n\n"
        "🌐 **Веб-дашборд:**\n"
        "https://yus.github.io/avitotiger/",
        parse_mode='Markdown'
    )

async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /search - поиск объявлений"""
    
    # Отправляем "печатает..."
    await send_typing_action(update)
    
    # Проверяем аргументы
    if not context.args:
        await update.message.reply_text(
            "❌ **Укажите запрос!**\n\n"
            "Пример: `/search iphone 13`",
            parse_mode='Markdown'
        )
        return
    
    query = ' '.join(context.args)
    
    # Отправляем статус
    status_msg = await update.message.reply_text(f"🔍 Ищем: {query}...")
    
    # Парсим
    parser = AvitoParser()
    ads = await parser.search(query)
    
    # Удаляем статус
    await status_msg.delete()
    
    if not ads:
        await update.message.reply_text(
            f"😕 По запросу **{query}** ничего не найдено",
            parse_mode='Markdown'
        )
        return
    
    # Отправляем результаты
    for i, ad in enumerate(ads[:5], 1):
        try:
            price = int(float(ad['price']))
            if price >= 1000:
                price_text = f"{price/1000:.0f} тыс ₽"
            else:
                price_text = f"{price} ₽"
        except:
            price_text = "Цена не указана"
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔗 Открыть объявление", url=ad['url'])]
        ])
        
        text = f"📌 **{i}.** {ad['title'][:80]}\n💰 **{price_text}**"
        if ad['location']:
            text += f"\n📍 {ad['location']}"
        
        await update.message.reply_text(
            text,
            parse_mode='Markdown',
            reply_markup=keyboard,
            disable_web_page_preview=False
        )
        await asyncio.sleep(0.3)

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка нажатий на кнопки"""
    query = update.callback_query
    await query.answer()
    
    if query.data.startswith('search_'):
        # Запускаем поиск из кнопки
        search_term = query.data.replace('search_', '')
        context.args = [search_term]
        await search_command(update, context)

# ===================== ЗАПУСК =====================

def main():
    """Запуск бота"""
    if not TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN не установлен!")
        return
    
    app = Application.builder().token(TOKEN).build()
    
    # Регистрируем команды
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("search", search_command))
    app.add_handler(CallbackQueryHandler(button_callback))
    
    print("🤖 Avito Tiger Bot запущен!")
    print("✅ Команда /search работает")
    
    # Запускаем
    app.run_polling(allowed_updates=['message', 'callback_query'])

if __name__ == "__main__":
    main()
