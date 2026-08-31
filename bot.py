import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("BOT_TOKEN environment variable is missing")

PAIRS = [
    ("EUR/USD OTC", "EURUSD_OTC"),
    ("GBP/USD OTC", "GBPUSD_OTC"),
    ("USD/JPY OTC", "USDJPY_OTC"),
    ("AUD/USD OTC", "AUDUSD_OTC"),
]

logging.basicConfig(level=logging.INFO)

def pair_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(name, callback_data=f"pair:{code}")]
        for name, code in PAIRS
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 OTC Live AI\n\nSelect an OTC pair:",
        reply_markup=pair_keyboard()
    )

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📊 Select OTC pair:",
        reply_markup=pair_keyboard()
    )

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    code = query.data.split(":", 1)[1]
    display = next((n for n, c in PAIRS if c == code), code)

    await query.edit_message_text(
        f"📊 {display}\n\n"
        "🟡 Live feed: waiting for verified market data\n"
        "🕯 Candle: not available yet\n"
        "📈 Signal: unavailable\n\n"
        "⚠️ No demo/random prices are used."
    )

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("menu", menu))
    app.add_handler(CallbackQueryHandler(button))
    app.run_polling()

if __name__ == "__main__":
    main()
