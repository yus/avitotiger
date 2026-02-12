#!/usr/bin/env python3
"""
Cron Parser for GitHub Actions - НИКАКОГО POLLING!
"""

import os
import asyncio
from datetime import datetime
from telegram import Bot

TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
ADMIN_IDS = os.getenv('TELEGRAM_ADMIN_IDS', '').split(',')

async def main():
    if not TOKEN:
        print('❌ Нет токена')
        return
    
    bot = Bot(token=TOKEN)
    
    # Просто отправляем пинг
    for admin_id in ADMIN_IDS:
        if admin_id:
            await bot.send_message(
                chat_id=int(admin_id),
                text=f'✅ Avito парсер работает\n🕐 {datetime.now().strftime("%H:%M:%S")}'
            )
    
    print('✅ Готово!')

if __name__ == '__main__':
    asyncio.run(main())