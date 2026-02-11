import aiohttp
import asyncio
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from tenacity import retry, stop_after_attempt, wait_exponential
from loguru import logger
from config.settings import Config

class AvitoParser:
    def __init__(self):
        self.ua = UserAgent()
        self.base_url = Config.AVITO_BASE_URL
        self.session = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, *args):
        await self.session.close()
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def search(self, query: str, category: str = None, location: str = None):
        """Поиск объявлений на Avito"""
        headers = {
            'User-Agent': self.ua.random,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        params = {
            'q': query,
            's': '1'  # Сортировка по дате
        }
        
        if category:
            params['categoryId'] = category
        if location:
            params['location'] = location
            
        try:
            async with self.session.get(
                f"{self.base_url}/rossiya",
                params=params,
                headers=headers,
                timeout=Config.REQUEST_TIMEOUT
            ) as response:
                if response.status == 200:
                    html = await response.text()
                    return self.parse_search_results(html)
                else:
                    logger.error(f"Avito returned {response.status}")
                    return []
        except Exception as e:
            logger.error(f"Error parsing Avito: {e}")
            return []
    
    def parse_search_results(self, html: str):
        """Парсинг результатов поиска"""
        soup = BeautifulSoup(html, 'html.parser')
        items = []
        
        # Поиск элементов объявлений
        ads = soup.select('[data-marker="item"]')
        
        for ad in ads[:10]:  # Ограничим 10 объявлениями
            try:
                title_elem = ad.select_one('[itemprop="name"]')
                price_elem = ad.select_one('[itemprop="price"]')
                link_elem = ad.select_one('a[href*="/"]')
                date_elem = ad.select_one('[data-marker="item-date"]')
                
                item = {
                    'title': title_elem.text.strip() if title_elem else 'No title',
                    'price': price_elem.get('content', '0') if price_elem else '0',
                    'url': f"{self.base_url}{link_elem.get('href')}" if link_elem else '',
                    'date': date_elem.text.strip() if date_elem else '',
                    'id': ad.get('id', '')
                }
                items.append(item)
            except Exception as e:
                logger.error(f"Error parsing ad: {e}")
                continue
                
        return items
