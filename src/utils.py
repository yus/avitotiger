from loguru import logger
import sys
from pathlib import Path
from config.settings import Config
from datetime import datetime

def setup_logging():
    """Настройка логирования"""
    Config.LOGS_DIR.mkdir(exist_ok=True)
    
    logger.remove()
    
    # Логирование в консоль
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level="INFO",
        colorize=True
    )
    
    # Логирование в файл
    logger.add(
        Config.LOGS_DIR / "bot_{time:YYYY-MM-DD}.log",
        rotation="500 MB",
        retention="30 days",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level="DEBUG",
        compression="gz"
    )

def format_price(price_str):
    """Форматирование цены"""
    try:
        price = int(price_str)
        if price >= 1000000:
            return f"{price/1000000:.1f} млн ₽"
        elif price >= 1000:
            return f"{price/1000:.0f} тыс ₽"
        else:
            return f"{price} ₽"
    except:
        return "Цена не указана"

def validate_url(url: str) -> bool:
    """Проверка валидности URL"""
    return url.startswith(('http://', 'https://'))

def truncate_text(text: str, max_length: int = 100) -> str:
    """Обрезка текста"""
    if len(text) > max_length:
        return text[:max_length - 3] + "..."
    return text
