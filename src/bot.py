#!/usr/bin/env python3
"""
Avito Tiger Bot - Telegram интерфейс
Запускается через GitHub Actions webhook
"""

import os
import sys
import json
import asyncio
from pathlib import Path
from datetime import datetime
import base64

sys.path.insert(0, str(Path(__file__).parent.parent))

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes
import aiohttp
from bs4 import BeautifulSoup
from fake_useragent import UserAgent

TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
ADMIN_IDS = list(map(int, os.getenv('TELEGRAM_ADMIN_IDS', '').split(','))) if os.getenv('TELEGRAM_ADMIN_IDS') else []

# ===================== ПАРСЕР =====================

class AvitoParser:
    """Быстрый парсер Avito"""
    
    BASE_URL = "https://www.avito.ru"
    
    def __init__(self):
        self.ua = UserAgent()
    
    async def search(self, query: str, limit: int = 5):
        async with aiohttp.ClientSession() as session:
            headers = {'User-Agent': self.ua.random}
            params = {'q': query}
            
            async with session.get(f"{self.BASE_URL}/rossiya", params=params, headers=headers) as resp:
                if resp.status != 200:
                    return []
                
                html = await resp.text()
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
                            'url': f"{self.BASE_URL}{link.get('href')}" if link else '',
                            'location': location.text.strip() if location else ''
                        })
                    except:
                        continue
                return ads

# ===================== КОМАНДЫ =====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Старт"""
    text = """
🤖 **Avito Tiger Bot**

🔍 **Мгновенный поиск:**
/search iphone 13 - найти объявления

📊 **Статистика Avito:**
/stats iphone - график цен
/trends - популярные запросы
/diagram - диаграмма категорий

📈 **Отчеты:**
/daily - отчет за день
/weekly - отчет за неделю

🌐 **Веб-дашборд:**
https://yus.github.io/avitotiger/
"""
    await update.message.reply_text(text, parse_mode='Markdown')

async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/search запрос - МГНОВЕННЫЙ ПОИСК"""
    if not context.args:
        await update.message.reply_text("❌ Укажите запрос: /search iphone 13")
        return
    
    query = ' '.join(context.args)
    await update.message.chat.send_action(action='typing')
    
    msg = await update.message.reply_text(f"🔍 Ищем: {query}...")
    
    parser = AvitoParser()
    ads = await parser.search(query)
    
    await msg.delete()
    
    if not ads:
        await update.message.reply_text(f"😕 Ничего не найдено по запросу: {query}")
        return
    
    for i, ad in enumerate(ads[:5], 1):
        price = int(float(ad['price'])) if ad['price'].isdigit() else 0
        if price >= 1000:
            price_text = f"{price/1000:.0f} тыс ₽"
        else:
            price_text = f"{price} ₽"
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔗 Открыть", url=ad['url'])]
        ])
        
        text = f"📌 **{i}.** {ad['title'][:80]}\n💰 **{price_text}**"
        if ad['location']:
            text += f"\n📍 {ad['location']}"
        
        await update.message.reply_text(text, parse_mode='Markdown', reply_markup=keyboard)
        await asyncio.sleep(0.3)

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/stats запрос - график цен"""
    if not context.args:
        await update.message.reply_text("❌ Укажите товар: /stats iphone 13")
        return
    
    query = ' '.join(context.args)
    
    # Загружаем историю цен
    prices_file = Path("data/prices.json")
    if not prices_file.exists():
        await update.message.reply_text("📊 Данных пока нет. Попробуйте позже.")
        return
    
    with open(prices_file) as f:
        data = json.load(f)
    
    if query not in data:
        await update.message.reply_text(f"📊 Нет данных по запросу: {query}")
        return
    
    # Генерируем диаграмму через GitHub Actions
    await update.message.reply_text(
        f"📊 Генерирую график цен для '{query}'...\n"
        f"⏱ Это займет несколько секунд"
    )
    
    # Запускаем workflow для генерации графика
    await trigger_workflow('generate_chart.yml', {
        'query': query,
        'chat_id': update.effective_chat.id
    })

async def diagram_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/diagram - диаграмма категорий"""
    # Ищем последнюю сгенерированную диаграмму
    diagrams_dir = Path("data/diagrams")
    if diagrams_dir.exists():
        diagrams = list(diagrams_dir.glob("*.png"))
        if diagrams:
            latest = max(diagrams, key=lambda p: p.stat().st_mtime)
            with open(latest, 'rb') as f:
                await update.message.reply_photo(photo=f)
            return
    
    await update.message.reply_text("📊 Генерирую диаграмму...")
    await trigger_workflow('generate_diagram.yml', {
        'chat_id': update.effective_chat.id
    })

async def daily_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/daily - отчет за день"""
    report_file = Path("data/daily_report.json")
    if report_file.exists():
        with open(report_file) as f:
            report = json.load(f)
        
        text = f"📊 **Отчет за {report['date']}**\n\n"
        text += f"🔍 Всего поисков: {report['total_searches']}\n"
        text += f"🆕 Новых объявлений: {report['new_ads']}\n"
        text += f"💰 Средняя цена: {report['avg_price']} ₽\n\n"
        text += f"🔥 **Топ-5 запросов:**\n"
        
        for i, (q, cnt) in enumerate(report['top_queries'][:5], 1):
            text += f"{i}. {q} — {cnt} раз\n"
        
        await update.message.reply_text(text, parse_mode='Markdown')
    else:
        await update.message.reply_text("📊 Отчет еще не сгенерирован. Попробуйте позже.")

async def trigger_workflow(workflow: str, payload: dict):
    """Запуск GitHub Actions workflow"""
    # Этот функционал добавим позже
    pass

# ===================== ЗАПУСК =====================

def main():
    if not TOKEN:
        print("❌ Нет токена!")
        return
    
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("search", search_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("diagram", diagram_command))
    app.add_handler(CommandHandler("daily", daily_command))
    app.add_handler(CommandHandler("trends", stats_command))
    app.add_handler(CommandHandler("weekly", daily_command))
    
    print("🤖 Avito Tiger Bot started!")
    app.run_polling()

if __name__ == "__main__":
    main()