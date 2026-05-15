import os
from dotenv import load_dotenv
from telebot import types
from groq import Groq
import telebot

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

bot = telebot.TeleBot(BOT_TOKEN)

client = Groq()

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message,
                 "Привет! Это AI-бот созданный на основе Groq\n"
                 "Можете писать запрос прямо в сообщениях боту. Самое время начать!\n"
                 )

@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    user_text = message.text
    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": user_text}]
        )
        bot.reply_to(message, response.choices[0].message.content)
    except Exception as e:
        bot.reply_to(message, f"Ошибка: {e}")

if __name__ == '__main__':
    print("Бот запущен...")
    bot.infinity_polling()