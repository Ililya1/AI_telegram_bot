import os
import requests
from dotenv import load_dotenv
import telebot
from telebot import types
from groq import Groq

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEATHERAPI_KEY = os.getenv("WEATHERAPI_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

bot = telebot.TeleBot(BOT_TOKEN)
client = Groq(api_key=GROQ_API_KEY)

user_states = {}

def get_current_weather(city: str):
    url = f"http://api.weatherapi.com/v1/current.json?key={WEATHERAPI_KEY}&q={city}&lang=ru"
    resp = requests.get(url)
    data = resp.json()
    if "error" in data:
        return None, data["error"]["message"]
    loc = data["location"]
    cur = data["current"]
    text = (
        f"{loc['name']}, {loc['country']}\n"
        f"Температура: {cur['temp_c']}°C (ощущается как {cur['feelslike_c']}°C)\n"
        f"️{cur['condition']['text']}\n"
        f"Ветер: {cur['wind_kph']} км/ч\n"
        f"Влажность: {cur['humidity']}%\n"
        f"Осадки: {cur.get('precip_mm', 0)} мм"
    )
    return text, None

def get_forecast_week(city: str):
    url = f"http://api.weatherapi.com/v1/forecast.json?key={WEATHERAPI_KEY}&q={city}&days=7&lang=ru"
    resp = requests.get(url)
    data = resp.json()
    if "error" in data:
        return None, data["error"]["message"]
    loc = f"{data['location']['name']}, {data['location']['country']}"
    forecast_days = data["forecast"]["forecastday"]
    text = f"Прогноз на неделю для {loc}:\n\n"
    for day in forecast_days:
        d = day["day"]
        text += (
            f" {day['date']}:  {d['mintemp_c']}…{d['maxtemp_c']}°C, "
            f"{d['condition']['text']}\n"
        )
    return text, None

def get_wearing_advice(city: str):
    weather_text, error = get_current_weather(city)
    if error:
        return None, error
    prompt = (
        f"Погода сейчас: {weather_text}\n\n"
        "Посоветуй, что надеть на улицу. Ответь кратко и практично: "
        "какую верхнюю одежду выбрать, нужен ли зонт, головной убор и т.п."
    )
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=300
    )
    advice = response.choices[0].message.content
    return advice, None

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message,
                 "Привет! Это AI-бот для анализа погоды на улице, созданный на основе Groq.\n"
                 "Используй /menu для выбора действия.\n"
                 "Рекомендация: для очередного запроса используй новое /menu, не обращайся к одному меню немсколько раз"
                )

@bot.message_handler(commands=['menu'])
def show_menu(message):
    markup = types.InlineKeyboardMarkup(row_width=1)
    btn_city = types.InlineKeyboardButton("Текущая погода", callback_data="city")
    btn_prognose = types.InlineKeyboardButton("Прогноз на неделю", callback_data="prognose")
    btn_wearing = types.InlineKeyboardButton("Что надеть", callback_data="wearing")
    markup.add(btn_city, btn_prognose, btn_wearing)
    bot.send_message(message.chat.id, "Выберите раздел:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    chat_id = call.message.chat.id
    if call.data == "city":
        user_states[chat_id] = "awaiting_city_current"
        bot.send_message(chat_id, "Введите название города:")
    elif call.data == "prognose":
        user_states[chat_id] = "awaiting_city_forecast"
        bot.send_message(chat_id, "Введите название города для прогноза на неделю:")
    elif call.data == "wearing":
        user_states[chat_id] = "awaiting_city_wearing"
        bot.send_message(chat_id, "Введите название города, чтобы узнать что надеть:")
    bot.answer_callback_query(call.id)

@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    chat_id = message.chat.id
    state = user_states.get(chat_id)
    if state == "awaiting_city_current":
        city = message.text.strip()
        user_states.pop(chat_id, None)
        result, error = get_current_weather(city)
        if error:
            bot.reply_to(message, f" Ошибка: {error}")
        else:
            bot.reply_to(message, result)
    elif state == "awaiting_city_forecast":
        city = message.text.strip()
        user_states.pop(chat_id, None)
        result, error = get_forecast_week(city)
        if error:
            bot.reply_to(message, f" Ошибка: {error}")
        else:
            bot.reply_to(message, result)
    elif state == "awaiting_city_wearing":
        city = message.text.strip()
        user_states.pop(chat_id, None)
        bot.reply_to(message, " Собираю данные и спрашиваю нейросеть...")
        result, error = get_wearing_advice(city)
        if error:
            bot.reply_to(message, f"Ошибка: {error}")
        else:
            bot.reply_to(message, f"*Совет по одежде:*\n{result}", parse_mode="Markdown")
    else:
        try:
            response = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "user", "content": message.text}]
            )
            bot.reply_to(message, response.choices[0].message.content)
        except Exception as e:
            bot.reply_to(message, f"Ошибка: {e}")

if __name__ == '__main__':
    print("Бот запущен...")
    bot.infinity_polling()