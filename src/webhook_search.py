#!/usr/bin/env python3
"""
Webhook Search Handler - Processes /search commands from GitHub Actions
"""

import os
import sys
import asyncio
from pathlib import Path

# Fix the path to find project root (3 levels up from src/)
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
import aiohttp
from bs4 import BeautifulSoup
from fake_useragent import UserAgent

async def main():
    # Get environment variables
    query = os.getenv('QUERY')
    chat_id = os.getenv('CHAT_ID')
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    
    if not all([query, chat_id, token]):
        print("❌ Missing required environment variables")
        return
    
    bot = Bot(token=token)
    ua = UserAgent()
    
    try:
        # Send typing action
        await bot.send_chat_action(chat_id=int(chat_id), action='typing')
        
        # Search Avito
        async with aiohttp.ClientSession() as session:
            headers = {'User-Agent': ua.random}
            params = {'q': query}
            
            async with session.get(
                "https://www.avito.ru/rossiya",
                params=params,
                headers=headers,
                timeout=30
            ) as response:
                
                if response.status != 200:
                    await bot.send_message(
                        chat_id=int(chat_id),
                        text=f"❌ Avito returned error {response.status}. Try again later."
                    )
                    return
                
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                # Find ads
                ads = soup.select('[data-marker="item"]')[:5]
                
                if not ads:
                    await bot.send_message(
                        chat_id=int(chat_id),
                        text=f"😕 No results found for: {query}"
                    )
                    return
                
                # Send each ad
                for ad in ads:
                    title_elem = ad.select_one('[itemprop="name"]')
                    price_elem = ad.select_one('[itemprop="price"]')
                    link_elem = ad.select_one('a[href*="/"]')
                    
                    title = title_elem.text.strip() if title_elem else "No title"
                    price = price_elem.get('content', '0') if price_elem else '0'
                    
                    if link_elem:
                        href = link_elem.get('href', '')
                        url = f"https://www.avito.ru{href}" if href.startswith('/') else href
                        
                        # Format price
                        try:
                            price_val = int(float(price))
                            if price_val >= 1000:
                                price_text = f"{price_val/1000:.0f} тыс ₽"
                            else:
                                price_text = f"{price_val} ₽"
                        except:
                            price_text = "Price not specified"
                        
                        keyboard = InlineKeyboardMarkup([
                            [InlineKeyboardButton("🔗 Open", url=url)]
                        ])
                        
                        await bot.send_message(
                            chat_id=int(chat_id),
                            text=f"🏷 **{title[:100]}**\n💰 **{price_text}**",
                            parse_mode='Markdown',
                            reply_markup=keyboard
                        )
                        await asyncio.sleep(0.3)
                
                await bot.send_message(
                    chat_id=int(chat_id),
                    text=f"✅ Found {len(ads)} ads for: {query}"
                )
                
    except Exception as e:
        error_msg = f"❌ Search error: {str(e)[:100]}"
        await bot.send_message(chat_id=int(chat_id), text=error_msg)
        print(error_msg)

if __name__ == "__main__":
    asyncio.run(main())
