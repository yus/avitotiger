import os
import json
import asyncio
from datetime import datetime
from telegram import Bot
from telegram.error import TelegramError

TOKEN = os.environ['TELEGRAM_BOT_TOKEN']
OFFSET_FILE = 'data/telegram_offset.txt'
QUEUE_DIR = 'data/queue'

async def poll_messages():
    """Get new messages from Telegram"""
    bot = Bot(token=TOKEN)
    
    # Get last processed update_id
    last_update_id = 0
    try:
        with open(OFFSET_FILE, 'r') as f:
            last_update_id = int(f.read().strip())
    except FileNotFoundError:
        pass
    
    try:
        # Get updates from Telegram
        updates = await bot.get_updates(
            offset=last_update_id,
            timeout=30,
            allowed_updates=['message']
        )
        
        if updates:
            print(f"📨 Received {len(updates)} updates")
            
            for update in updates:
                if update.message and update.message.text:
                    query = update.message.text.strip()
                    chat_id = update.message.chat_id
                    username = update.message.from_user.username or 'unknown'
                    
                    # Skip commands
                    if not query.startswith('/'):
                        # Save to queue
                        os.makedirs(QUEUE_DIR, exist_ok=True)
                        
                        search_request = {
                            'query': query,
                            'chat_id': chat_id,
                            'username': username,
                            'timestamp': datetime.now().isoformat(),
                            'update_id': update.update_id,
                            'status': 'pending'
                        }
                        
                        filename = f"{QUEUE_DIR}/{update.update_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}.json"
                        with open(filename, 'w', encoding='utf-8') as f:
                            json.dump(search_request, f, ensure_ascii=False, indent=2)
                        
                        print(f"✅ Queued search: '{query}' from @{username}")
                        
                        # Send immediate confirmation
                        await bot.send_message(
                            chat_id=chat_id,
                            text=f"🔍 Searching Avito for: *{query}*\n⏳ Results will appear in 1-3 minutes!",
                            parse_mode='Markdown'
                        )
            
            # Save next offset
            with open(OFFSET_FILE, 'w') as f:
                f.write(str(updates[-1].update_id + 1))
                
    except TelegramError as e:
        print(f"❌ Telegram error: {e}")

if __name__ == '__main__':
    asyncio.run(poll_messages())
