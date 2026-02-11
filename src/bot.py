import asyncio
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ConversationHandler
)
from config.settings import Config
from src.handlers import (
    start_command,
    help_command,
    add_search_handler,
    list_searches_handler,
    delete_search_handler,
    settings_handler,
    handle_callback,
    handle_text
)
from src.utils import setup_logging

async def main():
    # Настройка логирования
    setup_logging()
    
    # Создание приложения
    application = ApplicationBuilder()\
        .token(Config.TELEGRAM_BOT_TOKEN)\
        .concurrent_updates(True)\
        .build()
    
    # Регистрация обработчиков
    application.add_handler(CommandHandler('start', start_command))
    application.add_handler(CommandHandler('help', help_command))
    application.add_handler(CommandHandler('add', add_search_handler))
    application.add_handler(CommandHandler('list', list_searches_handler))
    application.add_handler(CommandHandler('delete', delete_search_handler))
    application.add_handler(CommandHandler('settings', settings_handler))
    
    # Обработчики callback и текста
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    # Запуск бота
    await application.run_polling(allowed_updates=['message', 'callback_query'])

if __name__ == '__main__':
    asyncio.run(main())
