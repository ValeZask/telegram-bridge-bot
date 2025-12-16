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

# Список матерных слов
MAT_WORDS = [
    # Основные и производные от "бля"
    'блять', 'блядь', 'бля', 'блят', 'бляь', 'бляд', 'блядина', 'блядовать', 'блядский', 'блядство', 'бляха', 'блях', 'бля буду', 'бля буду', 'блятский', 'блятьна', 'блясть',
    
    # Хуй и производные
    'хуй', 'хуя', 'хуи', 'хуё', 'хуев', 'хуёво', 'хуёвый', 'хуёво', 'хуесос', 'хуета', 'хуйло', 'хуйня', 'хуйня', 'нахуй', 'похуй', 'похер', 'нах', 'нахер', 'нахрен', 'до пизды', 'впизду', 'нахуя', 'нихуя', 'нихуясебе', 'хули', 'хуля', 'хуле', 'хуёк', 'хуище', 'хуило',
    
    # Пизд и производные
    'пизда', 'пиздец', 'пизду', 'пиздеть', 'пиздишь', 'пиздабол', 'пиздюк', 'пиздюлина', 'пиздюлей', 'пиздато', 'пиздатый', 'пиздеж', 'пиздобол', 'пиздюль', 'пиздюк', 'пиздобратия', 'пиздострадалица', 'пиздюрина', 'пиздишь', 'пиздеть', 'впизду',
    
    # Еб и производные
    'ебать', 'ебал', 'ебаный', 'ебануться', 'еби', 'ебло', 'еблан', 'ебу', 'ебаться', 'ёбнуть', 'ёбаный', 'ёб твою мать', 'еб твою мать', 'ебанутый', 'ебанулся', 'долбоёб', 'долбоеб', 'заебал', 'заебался', 'заебаться', 'заебись', 'проебать', 'проебался', 'выебываться', 'ебырь', 'ебала', 'ебучка', 'еблище',
    
    # Сука и производные
    'сука', 'суки', 'сучка', 'сучий', 'сучара', 'сукин', 'сукины дети', 'сучары', 'сучий потрох',
    
    # Говно/дерьмо
    'говно', 'говноед', 'говнюк', 'говна', 'говнецо', 'говнище', 'дерьмо', 'дерьмовый', 'дермо', 'говно вопрос', 'говнище',
    
    # Пидор и производные
    'пидор', 'пидорас', 'пидр', 'пидрас', 'пидрила', 'пидорок', 'пидорский',
    
    # Манда/мудак
    'манда', 'мандавошка', 'мудак', 'муда', 'муде', 'мудила', 'мудозвон', 'мудила', 'мудачок', 'мудень',
    
    # Жопа
    'жопа', 'жопу', 'вжопу', 'изжопы', 'жопастый', 'жопошник', 'поджопник',
    
    # Шлюха и синонимы
    'шлюха', 'шалава', 'шлюшка', 'курва', 'блядота', 'проститутка', 'шмара', 'давалька', 'шалавка',
    
    # Гандон и прочее
    'гандон', 'гондон', 'гнида', 'тварь', 'ублюдок', 'выродок', 'скотина', 'падла', 'падлюка',
    
    # Дополнительный мат и сленг
    'бляха-муха', 'ёбтвм', 'ебт', 'пидюлина', 'наебать', 'наебаться', 'отъебись', 'отъебаться', 'пиздаболка', 'пиздобратия', 'охуеть', 'охуенный', 'охуенно', 'охуевший', 'охуел', 'ахуеть', 'ахуенный', 'пиздец какой-то', 'полный пиздец', 'пиздец полный', 'пиздец нах', 'пиздуй', 'пиздюк', 'пошёл нахуй', 'иди нахуй', 'иди в жопу', 'пошел нахуй', 'идинах', 'пнх', 'пнхр', 'впнх', 'впх', 'пиздуй отсюда',
    
    # Английские и часто используемые
    'shit', 'sh1t', 'sh!t', 'fuck', 'fucking', 'fucked', 'fucker', 'motherfucker', 'mf', 'bitch', 'bitches', 'ass', 'asshole', 'dick', 'd1ck', 'cock', 'c0ck', 'pussy', 'cunt', 'whore', 'slut', 'sl*t', 'bastard', 'damn', 'dammit', 'hell', 'wtf', 'wtff', 'fck', 'fuk', 'fukin', 'fuking', 'sht', 'shyt', 'b1tch', 'b@tch', 'a55', 'a55hole'
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
    await asyncio.sleep(120)  # 2 минуты = 120 секунд
    await send_buffered_messages(context, sender_id, receiver_id)

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
    
    # Если отправитель - USER2, отправляем сразу с проверками
    fake_error = False
    error_message = ""
    
    if sender_id == USER2_ID:
        reset_counter_if_needed(sender_id)
        
        if message_counter.get(sender_id, 0) >= 5:
            fake_error = True
            error_message = "❌ Вы достигли ограничения, сообщение не было отправлено."
        
        text_to_check = update.message.text or update.message.caption or ""
        if check_mat(text_to_check):
            fake_error = True
            error_message = "❌ Ваш текст содержит нецензурные слова, сообщение не было передано."
        
        message_counter[sender_id] = message_counter.get(sender_id, 0) + 1
    
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
        
        if fake_error:
            await update.message.reply_text(error_message)
        else:
            await update.message.reply_text("✅ Сообщение отправлено!")
        
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