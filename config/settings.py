import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

class Config:
    # Telegram
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    TELEGRAM_ADMIN_IDS = list(map(int, os.getenv('TELEGRAM_ADMIN_IDS', '').split(',')))
    
    # Avito
    AVITO_BASE_URL = os.getenv('AVITO_BASE_URL', 'https://www.avito.ru')
    REQUEST_TIMEOUT = int(os.getenv('REQUEST_TIMEOUT', 30))
    MAX_RETRIES = int(os.getenv('MAX_RETRIES', 3))
    
    # Database
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///./avito_bot.db')
    
    # Paths
    BASE_DIR = Path(__file__).resolve().parent.parent
    LOGS_DIR = BASE_DIR / 'logs'
    DATA_DIR = BASE_DIR / 'data'
    
    # Bot settings
    BOT_NAME = "AvitoTigerBot"
    BOT_USERNAME = "avi2telegram_bot"
    BOT_VERSION = "1.0.0"
