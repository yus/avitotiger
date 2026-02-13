import os
import json
import requests
from datetime import datetime
from pathlib import Path
from bs4 import BeautifulSoup
import random
import re

TOKEN = os.environ['TELEGRAM_BOT_TOKEN']
QUEUE_DIR = 'data/queue'
PROCESSED_DIR = 'data/processed'
SEARCHES_DIR = 'data/searches'

def search_avito(query):
    """Search Avito and parse results"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'text/html,application/xhtml+xml',
        'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7'
    }
    
    # Avito search URL
    url = f'https://www.avito.ru/rossiya?q={requests.utils.quote(query)}'
    
    try:
        response = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        items = []
        # Find all listings
        listings = soup.select('[data-marker="item"]')
        
        for item in listings[:10]:  # Top 10 results
            title_elem = item.select_one('[itemprop="name"]')
            price_elem = item.select_one('[itemprop="price"]')
            link_elem = item.select_one('a[href*="/"]')
            
            if title_elem:
                title = title_elem.text.strip()
                price = price_elem.get('content', '0') if price_elem else '0'
                link = 'https://avito.ru' + link_elem.get('href', '') if link_elem else ''
                
                # Clean price
                price_clean = re.sub(r'[^\d]', '', str(price))
                
                items.append({
                    'title': title[:100],
                    'price': int(price_clean) if price_clean.isdigit() else 0,
                    'url': link,
                    'date': datetime.now().isoformat()
                })
        
        return items[:5]  # Return top 5
    except Exception as e:
        print(f"❌ Avito search error: {e}")
        return []

def send_telegram_results(chat_id, query, items):
    """Send search results to Telegram"""
    if not items:
        text = f"😕 No results found for *{query}*"
    else:
        text = f"🔍 *Results for: {query}*\n\n"
        for i, item in enumerate(items, 1):
            price = f"{item['price']:,} ₽".replace(',', ' ') if item['price'] else 'Цена не указана'
            text += f"{i}. [{item['title'][:50]}]({item['url']})\n💰 {price}\n\n"
    
    requests.post(
        f'https://api.telegram.org/bot{TOKEN}/sendMessage',
        json={
            'chat_id': chat_id,
            'text': text,
            'parse_mode': 'Markdown',
            'disable_web_page_preview': False
        }
    )

def save_search_history(query, items, chat_id, username):
    """Save to data/searches/ with date hierarchy"""
    today = datetime.now()
    year = today.strftime('%Y')
    month = today.strftime('%m')
    day = today.strftime('%d')
    
    # Create directory structure
    save_dir = Path(SEARCHES_DIR) / year / month / day
    save_dir.mkdir(parents=True, exist_ok=True)
    
    # Safe filename from query
    safe_query = re.sub(r'[^\w\s-]', '', query)[:30]
    safe_query = re.sub(r'[-\s]+', '_', safe_query)
    timestamp = today.strftime('%H%M%S')
    filename = f"{safe_query}_{timestamp}.json"
    
    search_data = {
        'query': query,
        'timestamp': today.isoformat(),
        'chat_id': chat_id,
        'username': username,
        'results_count': len(items),
        'avg_price': sum(i['price'] for i in items) // len(items) if items else 0,
        'items': items[:3]  # Store top 3 for dashboard
    }
    
    with open(save_dir / filename, 'w', encoding='utf-8') as f:
        json.dump(search_data, f, ensure_ascii=False, indent=2)
    
    print(f"💾 Saved search to {save_dir / filename}")

def process_queue():
    """Process all pending search requests"""
    # Create directories
    os.makedirs(QUEUE_DIR, exist_ok=True)
    os.makedirs(PROCESSED_DIR, exist_ok=True)
    os.makedirs(SEARCHES_DIR, exist_ok=True)
    
    # Get all pending searches
    queue_files = list(Path(QUEUE_DIR).glob('*.json'))
    
    if not queue_files:
        print("📭 No pending searches")
        return
    
    print(f"📋 Processing {len(queue_files)} searches...")
    
    for queue_file in queue_files:
        try:
            # Load request
            with open(queue_file, 'r', encoding='utf-8') as f:
                request = json.load(f)
            
            query = request['query']
            chat_id = request['chat_id']
            username = request.get('username', 'unknown')
            
            print(f"🔎 Searching: '{query}'")
            
            # Search Avito
            items = search_avito(query)
            
            # Send to Telegram
            send_telegram_results(chat_id, query, items)
            
            # Save to history
            save_search_history(query, items, chat_id, username)
            
            # Move to processed
            processed_path = Path(PROCESSED_DIR) / queue_file.name
            queue_file.rename(processed_path)
            
            print(f"✅ Completed: '{query}' ({len(items)} results)")
            
        except Exception as e:
            print(f"❌ Error processing {queue_file.name}: {e}")
            # Move failed to error dir
            error_dir = Path('data/error')
            error_dir.mkdir(exist_ok=True)
            queue_file.rename(error_dir / queue_file.name)

if __name__ == '__main__':
    process_queue()
