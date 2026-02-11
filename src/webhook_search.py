#!/usr/bin/env python3
"""
Обработчик вебхука для /search команды
Запускается через repository_dispatch
"""

import os
import sys
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
import aiohttp
from bs4 import BeautifulSoup
from fake_useragent import UserAgent

async def search_and_send():
    """Поиск и отправка результатов"""
    query = os.getenv('QUERY')
    chat_id = os.getenv('CHAT_ID')
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    
    if not all([query, chat_id, token]):
        print("❌ Missing required env vars")
        return
    
    bot = Bot(token=token)
    ua = UserAgent()
    
    # Отправляем "печатает..."
    await bot.send_chat_action(chat_id=int(chat_id), action='typing')
    
    # Парсим Avito
    async with aiohttp.ClientSession() as session:
        headers = {'User-Agent': ua.random}
        params = {'q': query}
        
        async with session.get(
            "https://www.avito.ru/rossiya",
            params=params,
            headers=headers
        ) as response:
            
            if response.status != 200:
                await bot.send_message(
                    chat_id=int(chat_id),
                    text=f"❌ Ошибка при поиске. Попробуйте позже."
                )
                return
            
            html = await response.text()
            soup = BeautifulSoup(html, 'html.parser')
            ads = []
            
            for item in soup.select('[data-marker="item"]')[:5]:
                try:
                    title = item.select_one('[itemprop="name"]')
                    price = item.select_one('[itemprop="price"]')
                    link = item.select_one('a[href*="/"]')
                    
                    ads.append({
                        'title': title.text.strip() if title else 'Без названия',
                        'price': price.get('content', '0') if price else '0',
                        'url': f"https://www.avito.ru{link.get('href')}" if link else ''
                    })
                except:
                    continue
    
    if not ads:
        await bot.send_message(
            chat_id=int(chat_id),
            text=f"😕 По запросу '{query}' ничего не найдено"
        )
        return
    
    for i, ad in enumerate(ads[:5], 1):
        price = int(float(ad['price'])) if ad['price'].isdigit() else 0
        price_text = f"{price/1000:.0f} тыс ₽" if price >= 1000 else f"{price} ₽"
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔗 Открыть", url=ad['url'])]
        ])
        
        await bot.send_message(
            chat_id=int(chat_id),
            text=f"📌 **{i}.** {ad['title'][:80]}\n💰 **{price_text}**",
            parse_mode='Markdown',
            reply_markup=keyboard
        )
        await asyncio.sleep(0.3)

if __name__ == "__main__":
    asyncio.run(search_and_send())
