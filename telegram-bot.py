import telebot
import random
import os

from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import datetime as dt
import requests

from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENWEATHER_KEY = os.getenv("OPENWEATHER_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

bot = telebot.TeleBot(TELEGRAM_TOKEN)

BASE_URL = 'http://api.openweathermap.org/data/2.5/weather?'

user_data = {}

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, f'Здарова {message.from_user.first_name}')

@bot.message_handler(commands=['help'])
def help_command(message):
    with open('files/help_info.txt', 'r', encoding='utf-8') as f:
        text = f.read()
        bot.send_message(message.chat.id, text)

@bot.message_handler(commands=['info'])
def info_command(message):
    with open('files/info_message.txt', 'r', encoding='utf-8') as f:
        text = f.read()
        bot.send_message(message.chat.id, text)

@bot.message_handler(commands=['meme'])
def meme_command(message):
    photos_dir = 'files/photos'
    all_photos = os.listdir(photos_dir)
    random_photo = random.choice(all_photos)
    with open(os.path.join(photos_dir, random_photo), 'rb') as photo:
        bot.send_photo(message.chat.id, photo)


@bot.message_handler(commands=['guess_num'])
def guess_num_start(message):
    chat_id = message.chat.id

    markup = InlineKeyboardMarkup(row_width=1)
    btn_easy = InlineKeyboardButton('Easy', callback_data='level_easy')
    btn_medium = InlineKeyboardButton('Medium', callback_data='level_medium')
    btn_hard = InlineKeyboardButton('Hard', callback_data='level_hard')
    markup.add(btn_easy, btn_medium, btn_hard)

    bot.send_message(chat_id, 'Обери складність гри:', reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('level_'))
def set_level(call):
    chat_id = call.message.chat.id

    if call.data == 'level_easy':
        number = random.randint(1, 10)
    elif call.data == 'level_medium':
        number = random.randint(1, 50)
    else:
        number = random.randint(1, 100)

    user_data[chat_id] = {"number": number, "attempts": 0}
    bot.send_message(chat_id, 'Я загадав число! Спробуй вгадати 😉')
    bot.register_next_step_handler(call.message, guess_number)

def guess_number(message):
    chat_id = message.chat.id

    if chat_id not in user_data:
        bot.send_message(chat_id, "Спочатку введи команду /guess_num")
        return

    try:
        guess = int(message.text)
    except ValueError:
        bot.send_message(chat_id, "Введи, будь ласка, число!")
        bot.register_next_step_handler(message, guess_number)
        return

    number = user_data[chat_id]["number"]
    user_data[chat_id]["attempts"] += 1

    if guess > number:
        bot.send_message(chat_id, 'Твоє число більше за загадане')
        bot.register_next_step_handler(message, guess_number)
    elif guess < number:
        bot.send_message(chat_id, 'Твоє число менше за загадане')
        bot.register_next_step_handler(message, guess_number)
    else:
        bot.send_message(chat_id, f'Молодець! Ти вгадав число {number} 🎉\n'
                                  f'Кількість спроб: {user_data[chat_id]["attempts"]}')
        del user_data[chat_id]

@bot.message_handler(func=lambda message: message.text == '/weather')
def weather_command(message):
    chat_id = message.chat.id
    bot.send_message(message.chat.id,'Введи назву міста/села англійською')


    bot.register_next_step_handler(message, send_weather_info)

def convertCalvines_to_Celsius(calvines):
    return calvines - 273.15

def send_weather_info(message=None, CITY=None):
    chat_id = message.chat.id if message else None

    if CITY is None:
        CITY = message.text

    if chat_id:
        user_data[chat_id] = {'City': CITY}

    url = BASE_URL + 'appid=' + OPENWEATHER_KEY + '&q=' + CITY
    response = requests.get(url).json()

    try:
        temp_calvines = response['main']['temp']
        temp_celsium = convertCalvines_to_Celsius(temp_calvines)

        feels_like_calvines = response['main']['feels_like']
        feels_like_celsium = convertCalvines_to_Celsius(feels_like_calvines)

        humidity = response['main']['humidity']
        wind_speed = response['wind']['speed']
        description = response['weather'][0]['description']

        sunrise_time = dt.datetime.fromtimestamp(response['sys']['sunrise'] + response['timezone'])
        sunset_time = dt.datetime.fromtimestamp(response['sys']['sunset'] + response['timezone'])

        weather_text = (
            f"🌆 Місто: {CITY.capitalize()}\n"
            f"☀️ Погода: {description.capitalize()}\n"
            f"🌡 Температура: {temp_celsium:.1f}°C\n"
            f"🤗 Відчувається як: {feels_like_celsium:.1f}°C\n"
            f"💧 Вологість: {humidity}%\n"
            f"💨 Вітер: {wind_speed} м/с\n"
            f"🌅 Схід сонця: {sunrise_time.strftime('%H:%M:%S')}\n"
            f"🌇 Захід сонця: {sunset_time.strftime('%H:%M:%S')}"
        )

        markup = InlineKeyboardMarkup(row_width=2)
        btn1 = InlineKeyboardButton(text='Оновити погоду', callback_data='weather_update')
        btn2 = InlineKeyboardButton(text='Обрати інше місто', callback_data='weather_change_city')
        markup.add(btn1, btn2)

        bot.send_message(chat_id, weather_text, reply_markup=markup)
    except KeyError:
        bot.send_message(chat_id, 'Місто не знайдено введи його ще раз')
        bot.register_next_step_handler(message, send_weather_info)


@bot.callback_query_handler(func=lambda call: call.data.startswith('weather'))
def weather_callback(call):
    chat_id = call.message.chat.id
    if call.data == 'weather_update':
        CITY = user_data[chat_id]['City']
        if CITY:
            send_weather_info(call.message, CITY)
        else:
            bot.send_message(chat_id, "Спочатку введи місто 🌆")
    elif call.data == 'weather_change_city':
        bot.send_message(chat_id, "Введи нове місто 🌆")
        bot.register_next_step_handler(call.message, send_weather_info)

@bot.message_handler(commands=['contacts'])
def contacts_command(message):
    chat_id = message.chat.id

    markup = InlineKeyboardMarkup(row_width=3)
    btn1 = InlineKeyboardButton(text='LinkedIn', callback_data='contact_LinkedIn', url = "https://www.linkedin.com/in/artem-dychenko-a0849a306/")
    btn2 = InlineKeyboardButton(text='Telegram', callback_data='contact_Telegram', url= "https://t.me/temmazavr")
    btn3 = InlineKeyboardButton(text='GitHub', callback_data='contact_GitHub', url = "https://github.com/Mierial")

    markup.add(btn1, btn2, btn3)
    bot.send_message(chat_id, 'Мої контакти для зв’язку 🙂', reply_markup=markup)

bot.polling(none_stop=True)
