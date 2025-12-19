import logging
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes, CommandHandler
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

# Отслеживание отправленных сообщений для USER1
sent_messages_to_track = {}  # Словарь {message_id: {receiver_id, sent: True}} для отслеживания доставки
user1_status_messages = {}  # Словарь {timer_id: message_id} для отслеживания уведомлений USER1

# Отслеживание блокировки USER2
user2_blocked = False

# Список матерных слов (включая корни и варианты)
MAT_WORDS = [
    # Русские матерные корни и вариации
    'блять', 'блядь', 'бля', 'ебля',
    'хуй', 'хуя', 'хуи', 'хую', 'хуе', 'хуем',
    'пизд', 'пиздец', 'пизда', 'пизде', 'пиздой', 'пиздули',
    'ебать', 'ебал', 'ебу', 'ебу', 'ебаный', 'ебаная', 'ебаное', 'ебаных',
    'еб', 'ебе', 'ебали', 'ебать',
    'сука', 'суки', 'сучка', 'сучек', 'сучатина', 'сучье',
    'говно', 'говна', 'говне', 'говнюк', 'говняк',
    'бляд', 'бляде', 'бляди',
    'хер', 'хера', 'хере', 'хероват',
    'шлюх', 'шлюха', 'шлюхи', 'шлюшка',
    'уёб', 'уёбок', 'уебок',
    'ёб', 'ёбаный', 'ебаный',
    'срать', 'серу', 'сру', 'срущ',
    'срака', 'сраку',
    'дерьмо', 'дерьма',
    'педик', 'педерас', 'педрила',
    'туп', 'тупица',
    'хню', 'хнею',
    'ссать', 'сру', 'сры',
    'козёл', 'козлина',
    'мудак', 'мудила',
    'ублюдок',
    'гавно', 'гавна',
    'гад', 'гадина',
    'засранец',
    'черт', 'чёрт',
    'нахуй', 'нахер', 'нахуя',
    'сраный', 'срать',
    'дохлый', 'дохлятина',
    'хвостач',
    'ябос',
    'сопля', 'соплюк',
    'корзина',
    'кочка', 'коченя',
    
    # Дополнительные оскорбительные слова и вариации
    'факю', 'факал', 'факаешь', 'факаю', 'факают',
    'какашка', 'какашки', 'какашку', 'какашкой',
    'ссыкун', 'ссыкуны', 'ссыканье', 'ссыкучий',
    'лох', 'лохи', 'лоха', 'лохам', 'лохами', 'лохов', 'лоховать',
    'дебил', 'дебилы', 'дебила', 'дебилизм',
    'идиот', 'идиоты', 'идиота', 'идиотизм',
    'кретин', 'кретины', 'кретина', 'кретинизм',
    'придурок', 'придурки', 'придурков',
    'урод', 'уроды', 'урода', 'уродский', 'уродство',
    'чмо', 'чмошник', 'чмошники',
    'баран', 'бараны', 'баранина', 'баранский',
    'овца', 'овцы', 'овцой',
    'осел', 'ослы', 'ослиный',
    'свинья', 'свиньи', 'свинью', 'свинской',
    'крыса', 'крысы', 'крысой',
    'гавно', 'гавна', 'гавнюк',
    'жмот', 'жмоты', 'жмотство',
    'грязь', 'грязный', 'грязнуля',
    'паразит', 'паразиты', 'паразитизм',
    'полоумный', 'полудурок',
    'рохля', 'роханье', 'рохлый',
    'болван', 'болваны', 'болванить',
    'простак', 'простаки',
    'недалекий', 'недалеко',
    'слюнтяй', 'слюнтяи',
    'тряпка', 'тряпки', 'тряпочка',
    'тупой', 'тупица', 'тупень',
    'спамер', 'спамеры', 'спамить',
    'троль', 'тролли', 'троллить',
    'бок',
    
    # Английские матерные слова
    'shit', 'shitty', 'shitting',
    'fuck', 'fucking', 'fucker', 'fucked', 'fuckery', 'fuckhead', 'fuckwit',
    'bitch', 'bitchy', 'bitches',
    'ass', 'asshole', 'asses',
    'dick', 'dickhead', 'dicks',
    'pussy', 'pussies',
    'damn', 'dammit', 'damned',
    'hell', 'hellish',
    'bastard', 'bastards',
    'crap', 'crappy',
    'cock', 'cocky', 'cocksucker',
    'whore', 'whores',
    'slut', 'sluts',
    'cunt', 'cunts',
    'twat', 'twats',
    'arse', 'arses',
    'piss', 'pissed',
    'bollocks',
    'wanker', 'wankers',
    'bugger',
    'idiot', 'idiots', 'idiotic',
    'moron', 'morons', 'moronic',
    'retard', 'retards',
    'asshat', 'asshats',
    'jerk', 'jerks', 'jerkoff',
    'douchebag', 'douchebags',
    'dumbass', 'dumbasses',
    'assclown', 'assclowns',
    'arse',
    'bollocks'
]

def reset_counter_if_needed(user_id):
    """Сбрасывает счетчик если наступил новый день"""
    today = datetime.now().date()
    
    if user_id not in last_reset_date or last_reset_date[user_id] != today:
        message_counter[user_id] = 0
        last_reset_date[user_id] = today

def check_mat(text):
    """Проверяет текст на мат с учетом вариаций"""
    if not text:
        return False
    
    # Очищаем текст от специальных символов, цифр и пробелов, но сохраняем буквы
    # Преобразуем в нижний регистр
    text_lower = text.lower()
    
    # Заменяем кириллицу на похожие латинские символы и наоборот
    # для ловления попыток обхода цензуры
    replacements = {
        'о': '[о0oоО]',
        'е': '[еeéеЕ]',
        'а': '[аaаА]',
        'и': '[иiиИ]',
        'у': '[уuуУ]',
        'ы': '[ыyыЫ]',
        'э': '[эeэЭ]',
        'я': '[яяЯ]',
    }
    
    for word in MAT_WORDS:
        # Создаем паттерн с учетом возможных замен
        pattern = word
        
        # Подставляем регулярные выражения для похожих символов
        for cyrillic, regex_pattern in replacements.items():
            pattern = pattern.replace(cyrillic, regex_pattern)
        
        # Ищем слово с граничками (не часть другого слова)
        # и добавляем допуск на специальные символы между буквами
        flexible_pattern = r'(?:[^а-яё0-9a-z]|^)' + pattern + r'(?:[^а-яё0-9a-z]|$)'
        
        if re.search(flexible_pattern, text_lower, re.IGNORECASE):
            return True
    
    return False

async def send_buffered_messages(context: ContextTypes.DEFAULT_TYPE, sender_id: int, receiver_id: int, status_msg_id: int = None):
    """Отправляет все накопленные сообщения"""
    
    if sender_id not in message_buffer or not message_buffer[sender_id]:
        return
    
    messages = message_buffer[sender_id]
    message_count = len(messages)
    message_buffer[sender_id] = []
    
    # Отправляем все накопленные сообщения
    for msg_data in messages:
        try:
            msg_type = msg_data['type']
            sent_msg = None
            
            if msg_type == 'text':
                sent_msg = await context.bot.send_message(
                    chat_id=receiver_id,
                    text=msg_data['text']
                )
            elif msg_type == 'photo':
                sent_msg = await context.bot.send_photo(
                    chat_id=receiver_id,
                    photo=msg_data['file_id'],
                    caption=msg_data.get('caption', '')
                )
            elif msg_type == 'video':
                sent_msg = await context.bot.send_video(
                    chat_id=receiver_id,
                    video=msg_data['file_id'],
                    caption=msg_data.get('caption', '')
                )
            elif msg_type == 'document':
                sent_msg = await context.bot.send_document(
                    chat_id=receiver_id,
                    document=msg_data['file_id'],
                    caption=msg_data.get('caption', '')
                )
            elif msg_type == 'voice':
                sent_msg = await context.bot.send_voice(
                    chat_id=receiver_id,
                    voice=msg_data['file_id']
                )
            elif msg_type == 'audio':
                sent_msg = await context.bot.send_audio(
                    chat_id=receiver_id,
                    audio=msg_data['file_id'],
                    caption=msg_data.get('caption', '')
                )
            elif msg_type == 'sticker':
                sent_msg = await context.bot.send_sticker(
                    chat_id=receiver_id,
                    sticker=msg_data['file_id']
                )
            elif msg_type == 'video_note':
                sent_msg = await context.bot.send_video_note(
                    chat_id=receiver_id,
                    video_note=msg_data['file_id']
                )
            
            # Отслеживаем отправленное сообщение
            if sent_msg:
                if sender_id not in sent_messages_to_track:
                    sent_messages_to_track[sender_id] = {}
                sent_messages_to_track[sender_id][sent_msg.message_id] = {
                    'receiver_id': receiver_id,
                    'sent': True
                }
                
        except Exception as e:
            logging.error(f"Ошибка при отправке накопленного сообщения: {e}")
    
    # Отправляем уведомление USER1 о доставке сообщений
    try:
        message_text = f"✅ Отправлено сообщение{'й' if message_count == 1 else 'й'}: {message_count}"
        if status_msg_id:
            await context.bot.edit_message_text(
                chat_id=sender_id,
                message_id=status_msg_id,
                text=message_text
            )
        else:
            await context.bot.send_message(
                chat_id=sender_id,
                text=message_text
            )
    except Exception as e:
        logging.error(f"Ошибка при отправке уведомления о доставке: {e}")
    
    # Очищаем задачу таймера
    if sender_id in timer_task:
        del timer_task[sender_id]

async def start_timer(context: ContextTypes.DEFAULT_TYPE, sender_id: int, receiver_id: int, status_msg_id: int = None):
    """Запускает таймер на 2 минуты"""
    try:
        await asyncio.sleep(120)  # 2 минуты = 120 секунд
        await send_buffered_messages(context, sender_id, receiver_id, status_msg_id)
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
            status_msg = await update.message.reply_text(f"⏳ Ваше сообщение добавлено в очередь. Будет отправлено через 2 минуты (всего в очереди: {len(message_buffer[sender_id])})")
            timer_task[sender_id] = asyncio.create_task(
                start_timer(context, sender_id, receiver_id, status_msg.message_id)
            )
        else:
            await update.message.reply_text(f"⏳ Ваше сообщение добавлено в очередь (всего: {len(message_buffer[sender_id])})")
        
        return
    
    # Если отправитель - USER2, проверяем блокировку и лимиты
    global user2_blocked
    if sender_id == USER2_ID:
        reset_counter_if_needed(sender_id)
        
        text_to_check = update.message.text or update.message.caption or ""
        has_mat = check_mat(text_to_check)
        
        # Проверяем наличие мата
        if has_mat:
            # Отправляем уведомление USER2 о мате
            await update.message.reply_text("❌ Ваш текст содержит нецензурные слова, сообщение не было передано.")
            # Блокируем USER2
            user2_blocked = True
            # Сообщение все равно отправится USER1 (продолжаем выполнение)
        
        # Проверяем, уже ли USER2 заблокирован (после первого мата или 5 сообщений)
        elif user2_blocked:
            await update.message.reply_text("❌ Вы достигли ограничения, сообщение не было отправлено.")
            # Сообщение все равно отправится USER1 (продолжаем выполнение)
        
        # Если не мат и не заблокирован - считаем сообщение
        else:
            message_counter[sender_id] = message_counter.get(sender_id, 0) + 1
            # Проверяем, достигнут ли лимит в 5 сообщений
            if message_counter[sender_id] >= 5:
                user2_blocked = True
    
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
        
        # Отправляем подтверждение USER2 если сообщение было успешно отправлено
        # (только если нет мата и не заблокирован)
        if not has_mat and not user2_blocked:
            await update.message.reply_text("✅ Сообщение отправлено!")
        
    except Exception as e:
        logging.error(f"Ошибка при пересылке сообщения: {e}")
        await update.message.reply_text("❌ Ошибка при отправке сообщения.")

async def handle_message_reaction(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик для отслеживания прочтения сообщений через реакцию"""
    try:
        if update.message_reaction:
            user_id = update.message_reaction.user_id
            msg_id = update.message_reaction.message_id
            chat_id = update.message_reaction.chat_id
            
            # Если USER2 добавил реакцию на сообщение в приватном чате
            if user_id == USER2_ID and chat_id == USER2_ID:
                # Проверяем, есть ли это сообщение в нашем отслеживании
                if USER1_ID in sent_messages_to_track and msg_id in sent_messages_to_track[USER1_ID]:
                    try:
                        await context.bot.send_message(
                            chat_id=USER1_ID,
                            text="👁️ Ваше сообщение было прочтено"
                        )
                        # Удаляем из отслеживания
                        del sent_messages_to_track[USER1_ID][msg_id]
                    except Exception as e:
                        logging.error(f"Ошибка при отправке уведомления о прочтении: {e}")
    except Exception as e:
        logging.error(f"Ошибка в обработчике message_reaction: {e}")

async def mark_as_read(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда для USER2 чтобы отметить последнее сообщение как прочитанное"""
    user_id = update.effective_user.id
    
    # Проверяем, что это USER2
    if user_id != USER2_ID:
        await update.message.reply_text("❌ У вас нет доступа к этой команде.")
        return
    
    # Получаем последнее сообщение из отслеживания USER1
    if USER1_ID in sent_messages_to_track and sent_messages_to_track[USER1_ID]:
        try:
            # Берем последнее отслеживаемое сообщение
            last_msg_id = list(sent_messages_to_track[USER1_ID].keys())[-1]
            
            # Отправляем уведомление USER1
            await context.bot.send_message(
                chat_id=USER1_ID,
                text="👁️ Ваше сообщение было прочтено"
            )
            
            # Удаляем из отслеживания
            del sent_messages_to_track[USER1_ID][last_msg_id]
            
            await update.message.reply_text("✅ Сообщение отмечено как прочитанное")
        except Exception as e:
            logging.error(f"Ошибка при отметке сообщения: {e}")
            await update.message.reply_text("❌ Ошибка при отметке сообщения.")
    else:
        await update.message.reply_text("ℹ️ Нет непрочитанных сообщений.")

def main():
    """Запуск бота"""
    
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Обработчик сообщений
    application.add_handler(MessageHandler(
        filters.ALL & ~filters.COMMAND,
        forward_message
    ))
    
    # Обработчик команды /marked_as_read
    application.add_handler(CommandHandler("marked_as_read", mark_as_read))
    
    print("🤖 Бот запущен и готов к работе!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()