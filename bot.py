"""Ombor360 Telegram bot (MVP).

Ishga tushirish:
1) .env ichiga TELEGRAM_BOT_TOKEN yozing.
2) python bot.py

Bu bot hozir xodimga web-dastur havolasini beradi. Keyingi bosqichda
pul so‘rovi, rahbar tasdig‘i va kassir tugmalarini to‘liq Telegram ichiga ko‘chirish mumkin.
"""
import os
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes

load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
BASE_URL = os.getenv("PUBLIC_BASE_URL", "http://localhost:5000")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("Ombor360° ni ochish", url=BASE_URL)]])
    await update.message.reply_text(
        "Ombor360° botiga xush kelibsiz. Pul so‘rovi va o‘z hisobingizni web kabinetda boshqarishingiz mumkin.",
        reply_markup=kb,
    )

if __name__ == "__main__":
    if not TOKEN:
        raise SystemExit("TELEGRAM_BOT_TOKEN topilmadi")
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.run_polling()
