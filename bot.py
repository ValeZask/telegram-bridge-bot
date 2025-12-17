import logging
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from datetime import datetime, timedelta
import re
import asyncio
import os
from dotenv import load_dotenv

# Загружаем переменные из .env файла
load_dotenv()

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Получаем данные из переменных окружения
BOT_TOKEN = os.getenv("BOT_TOKEN")
USER1_ID = int(os.getenv("USER1_ID"))
USER2_ID = int(os.getenv("USER2_ID"))

# Счетчик сообщений для USER2
message_counter = {}
last_reset_date = {}

# Буфер сообщений для USER1
message_buffer = {}
timer_task = {}

# Отслеживание блокировки USER2
user2_blocked = False

# Список матерных слов
MAT_WORDS = [
    'блять', 'блядь', 'бля', 'хуй', 'хуя', 'хуи', 'пизда', 'пиздец', 
    'ебать', 'ебал', 'ебаный', 'сука', 'суки', 'сучка', 'говно',
    'shit', 'fuck', 'bitch', 'ass', 'dick', 'pussy'
]

def reset_counter_if_needed(user_id):
    """Сбрасывает счетчик если наступил новый день"""
    today = datetime.now().date()
    
    if user_id not in last_reset_date or last_reset_date[user_id] != today:
        message_counter[user_id] = 0
        last_reset_date[user_id] = today

def check_mat(text):
    """Проверяет текст на мат"""
    if not text:
        return False
    
    text_lower = text.lower()
    for word in MAT_WORDS:
        if re.search(r'\b' + word + r'\b', text_lower):
            return True
    return False

async def send_buffered_messages(context: ContextTypes.DEFAULT_TYPE, sender_id: int, receiver_id: int):
    """Отправляет все накопленные сообщения"""
    
    if sender_id not in message_buffer or not message_buffer[sender_id]:
        return
    
    messages = message_buffer[sender_id]
    message_buffer[sender_id] = []
    
    # Отправляем все накопленные сообщения
    for msg_data in messages:
        try:
            msg_type = msg_data['type']
            
            if msg_type == 'text':
                await context.bot.send_message(
                    chat_id=receiver_id,
                    text=msg_data['text']
                )
            elif msg_type == 'photo':
                await context.bot.send_photo(
                    chat_id=receiver_id,
                    photo=msg_data['file_id'],
                    caption=msg_data.get('caption', '')
                )
            elif msg_type == 'video':
                await context.bot.send_video(
                    chat_id=receiver_id,
                    video=msg_data['file_id'],
                    caption=msg_data.get('caption', '')
                )
            elif msg_type == 'document':
                await context.bot.send_document(
                    chat_id=receiver_id,
                    document=msg_data['file_id'],
                    caption=msg_data.get('caption', '')
                )
            elif msg_type == 'voice':
                await context.bot.send_voice(
                    chat_id=receiver_id,
                    voice=msg_data['file_id']
                )
            elif msg_type == 'audio':
                await context.bot.send_audio(
                    chat_id=receiver_id,
                    audio=msg_data['file_id'],
                    caption=msg_data.get('caption', '')
                )
            elif msg_type == 'sticker':
                await context.bot.send_sticker(
                    chat_id=receiver_id,
                    sticker=msg_data['file_id']
                )
            elif msg_type == 'video_note':
                await context.bot.send_video_note(
                    chat_id=receiver_id,
                    video_note=msg_data['file_id']
                )
                
        except Exception as e:
            logging.error(f"Ошибка при отправке накопленного сообщения: {e}")
    
    # Очищаем задачу таймера
    if sender_id in timer_task:
        del timer_task[sender_id]

async def start_timer(context: ContextTypes.DEFAULT_TYPE, sender_id: int, receiver_id: int):
    """Запускает таймер на 2 минуты"""
    try:
        await asyncio.sleep(120)  # 2 минуты = 120 секунд
        await send_buffered_messages(context, sender_id, receiver_id)
    except asyncio.CancelledError:
        pass

async def forward_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Пересылает сообщения между двумя пользователями"""
    
    sender_id = update.effective_user.id
    
    # Проверяем, что сообщение от одного из двух пользователей
    if sender_id not in [USER1_ID, USER2_ID]:
        await update.message.reply_text("❌ У вас нет доступа к этому боту.")
        return
    
    # Определяем получателя
    receiver_id = USER2_ID if sender_id == USER1_ID else USER1_ID
    
    # Если отправитель - USER1, используем буферизацию
    if sender_id == USER1_ID:
        # Инициализируем буфер если нужно
        if sender_id not in message_buffer:
            message_buffer[sender_id] = []
        
        # Добавляем сообщение в буфер
        msg_data = {}
        
        if update.message.text:
            msg_data = {'type': 'text', 'text': update.message.text}
        elif update.message.photo:
            photo = update.message.photo[-1]
            msg_data = {
                'type': 'photo',
                'file_id': photo.file_id,
                'caption': update.message.caption or ''
            }
        elif update.message.video:
            msg_data = {
                'type': 'video',
                'file_id': update.message.video.file_id,
                'caption': update.message.caption or ''
            }
        elif update.message.document:
            msg_data = {
                'type': 'document',
                'file_id': update.message.document.file_id,
                'caption': update.message.caption or ''
            }
        elif update.message.voice:
            msg_data = {'type': 'voice', 'file_id': update.message.voice.file_id}
        elif update.message.audio:
            msg_data = {
                'type': 'audio',
                'file_id': update.message.audio.file_id,
                'caption': update.message.caption or ''
            }
        elif update.message.sticker:
            msg_data = {'type': 'sticker', 'file_id': update.message.sticker.file_id}
        elif update.message.video_note:
            msg_data = {'type': 'video_note', 'file_id': update.message.video_note.file_id}
        else:
            await update.message.reply_text("⚠️ Этот тип сообщения пока не поддерживается.")
            return
        
        message_buffer[sender_id].append(msg_data)
        
        # Запускаем таймер если он еще не запущен
        if sender_id not in timer_task or timer_task[sender_id].done():
            timer_task[sender_id] = asyncio.create_task(
                start_timer(context, sender_id, receiver_id)
            )
            await update.message.reply_text(f"⏳ Сообщение добавлено в очередь. Будет отправлено через 2 минуты (всего в очереди: {len(message_buffer[sender_id])})")
        else:
            await update.message.reply_text(f"⏳ Сообщение добавлено в очередь (всего: {len(message_buffer[sender_id])})")
        
        return
    
    # Если отправитель - USER2, проверяем блокировку
    global user2_blocked
    if sender_id == USER2_ID:
        reset_counter_if_needed(sender_id)
        
        # Если USER2 уже заблокирован, отправляем сообщение об ограничении
        if user2_blocked:
            await update.message.reply_text("❌ Вы достигли ограничения, сообщение не было отправлено.")
            return
        
        text_to_check = update.message.text or update.message.caption or ""
        if check_mat(text_to_check):
            # Отправляем уведомление USER2 о мате
            await update.message.reply_text("❌ Ваш текст содержит нецензурные слова, сообщение не было передано.")
            # НО сообщение все равно отправляется USER1
            user2_blocked = True
            # Продолжаем обработку для отправки USER1
    
    try:
        # Отправляем сообщение сразу для USER2
        if update.message.text:
            await context.bot.send_message(
                chat_id=receiver_id,
                text=update.message.text
            )
        elif update.message.photo:
            photo = update.message.photo[-1]
            caption = update.message.caption or ""
            await context.bot.send_photo(
                chat_id=receiver_id,
                photo=photo.file_id,
                caption=caption
            )
        elif update.message.video:
            caption = update.message.caption or ""
            await context.bot.send_video(
                chat_id=receiver_id,
                video=update.message.video.file_id,
                caption=caption
            )
        elif update.message.document:
            caption = update.message.caption or ""
            await context.bot.send_document(
                chat_id=receiver_id,
                document=update.message.document.file_id,
                caption=caption
            )
        elif update.message.voice:
            await context.bot.send_voice(
                chat_id=receiver_id,
                voice=update.message.voice.file_id
            )
        elif update.message.audio:
            caption = update.message.caption or ""
            await context.bot.send_audio(
                chat_id=receiver_id,
                audio=update.message.audio.file_id,
                caption=caption
            )
        elif update.message.sticker:
            await context.bot.send_sticker(
                chat_id=receiver_id,
                sticker=update.message.sticker.file_id
            )
        elif update.message.video_note:
            await context.bot.send_video_note(
                chat_id=receiver_id,
                video_note=update.message.video_note.file_id
            )
        else:
            await update.message.reply_text("⚠️ Этот тип сообщения пока не поддерживается.")
            return
        
        # USER2 отправил сообщение - не нужно уведомление об успехе
        # (потому что они либо видят, что сообщение содержит мат, либо достигли лимита)
        
    except Exception as e:
        logging.error(f"Ошибка при пересылке сообщения: {e}")
        await update.message.reply_text("❌ Ошибка при отправке сообщения.")

def main():
    """Запуск бота"""
    
    application = Application.builder().token(BOT_TOKEN).build()
    
    application.add_handler(MessageHandler(
        filters.ALL & ~filters.COMMAND,
        forward_message
    ))
    
    print("🤖 Бот запущен и готов к работе!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()