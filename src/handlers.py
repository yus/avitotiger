from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from loguru import logger
from src.database import Database
from src.avito_parser import AvitoParser
from src.utils import format_price
import json

db = Database()

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    user = update.effective_user
    
    # Сохраняем пользователя в БД
    db_user = db.get_user(user.id)
    if not db_user:
        db.add_user(
            telegram_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name
        )
    
    welcome_text = f"""
👋 Привет, {user.first_name}!

Я бот для мониторинга объявлений на Avito.
Я могу уведомлять тебя о новых объявлениях по твоим поисковым запросам.

📝 Доступные команды:
/start - показать это сообщение
/add - добавить новый поиск
/list - список активных поисков
/delete - удалить поиск
/settings - настройки
/help - помощь

🎯 Чтобы начать, просто отправь /add
    """
    
    await update.message.reply_text(welcome_text)

async def add_search_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало добавления нового поиска"""
    context.user_data['state'] = 'awaiting_query'
    await update.message.reply_text(
        "🔍 Введите поисковый запрос (например: 'iPhone 13'):"
    )

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка текстовых сообщений"""
    state = context.user_data.get('state')
    
    if state == 'awaiting_query':
        context.user_data['search_query'] = update.message.text
        context.user_data['state'] = 'awaiting_confirmation'
        
        # Предварительный поиск
        async with AvitoParser() as parser:
            results = await parser.search(update.message.text)
            
        if results:
            preview = "📊 Найдены объявления:\n\n"
            for item in results[:3]:
                preview += f"🏷 {item['title'][:50]}...\n"
                preview += f"💰 {format_price(item['price'])}\n"
                preview += f"🔗 {item['url']}\n\n"
            
            await update.message.reply_text(
                f"✅ Запрос: '{update.message.text}'\n\n"
                f"{preview}"
                f"Сохранить этот поиск?",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("✅ Да", callback_data="save_search"),
                     InlineKeyboardButton("❌ Нет", callback_data="cancel_search")]
                ])
            )
        else:
            await update.message.reply_text(
                "❌ По вашему запросу ничего не найдено. Попробуйте другой запрос:"
            )
    
    elif state == 'awaiting_delete':
        try:
            search_id = int(update.message.text)
            user = db.get_user(update.effective_user.id)
            
            if db.delete_search(search_id, user.id):
                await update.message.reply_text("✅ Поиск успешно удален!")
            else:
                await update.message.reply_text("❌ Поиск с таким ID не найден")
        except ValueError:
            await update.message.reply_text("❌ Пожалуйста, введите корректный ID")
        
        context.user_data.pop('state', None)

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка callback запросов"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "save_search":
        user = db.get_user(update.effective_user.id)
        search_query = context.user_data.get('search_query')
        
        saved_search = db.add_search_query(
            user_id=user.id,
            query=search_query
        )
        
        if saved_search:
            await query.edit_message_text(
                f"✅ Поиск сохранен!\n"
                f"ID: {saved_search.id}\n"
                f"Запрос: {search_query}\n\n"
                f"Я буду уведомлять вас о новых объявлениях."
            )
        else:
            await query.edit_message_text("❌ Ошибка при сохранении поиска")
        
        context.user_data.pop('state', None)
        context.user_data.pop('search_query', None)
    
    elif query.data == "cancel_search":
        await query.edit_message_text("❌ Поиск отменен")
        context.user_data.pop('state', None)
        context.user_data.pop('search_query', None)

async def list_searches_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать список активных поисков"""
    user = db.get_user(update.effective_user.id)
    searches = db.get_user_searches(user.id)
    
    if not searches:
        await update.message.reply_text(
            "📭 У вас нет активных поисков.\n"
            "Добавьте новый с помощью /add"
        )
        return
    
    text = "📋 Ваши активные поиски:\n\n"
    for search in searches:
        text += f"🆔 ID: {search.id}\n"
        text += f"🔍 Запрос: {search.query}\n"
        if search.category:
            text += f"📁 Категория: {search.category}\n"
        if search.min_price or search.max_price:
            text += f"💰 Цена: "
            if search.min_price:
                text += f"от {search.min_price}"
            if search.max_price:
                text += f" до {search.max_price}"
            text += "\n"
        text += f"📅 Создан: {search.created_at.strftime('%d.%m.%Y')}\n\n"
    
    await update.message.reply_text(text)

async def delete_search_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Удаление поиска"""
    context.user_data['state'] = 'awaiting_delete'
    await update.message.reply_text(
        "🗑 Введите ID поиска, который хотите удалить:\n"
        "(ID можно посмотреть в /list)"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Справка по командам"""
    help_text = """
📚 Справка по командам:

/add - добавить новый поисковый запрос
/list - посмотреть все активные поиски
/delete - удалить поиск
/settings - настройки уведомлений
/help - эта справка

💡 Советы:
• Используйте точные запросы для лучших результатов
• Можно фильтровать по цене (скоро)
• Уведомления приходят раз в 15 минут

❓ По вопросам: @admin
    """
    await update.message.reply_text(help_text)

async def settings_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Настройки пользователя"""
    keyboard = [
        [InlineKeyboardButton("🔔 Частота уведомлений", callback_data="settings_notify")],
        [InlineKeyboardButton("📊 Макс. объявлений", callback_data="settings_max")],
        [InlineKeyboardButton("🏷 Категории", callback_data="settings_categories")],
        [InlineKeyboardButton("◀️ Назад", callback_data="settings_back")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "⚙️ Настройки бота:\n\n"
        "Выберите параметр для изменения:",
        reply_markup=reply_markup
    )
