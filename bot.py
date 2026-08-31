import os
import asyncio
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from BinomoAPI.api import BinomoAPI

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("otc-bot")

TOKEN = os.getenv("BOT_TOKEN")
BINOMO_EMAIL = os.getenv("BINOMO_EMAIL")
BINOMO_PASSWORD = os.getenv("BINOMO_PASSWORD")
DEVICE_ID = os.getenv("BINOMO_DEVICE_ID", "1b6290ce761c82f3a97189d35d2ed138")

if not TOKEN:
    raise RuntimeError("BOT_TOKEN is missing")

api = None
otc_assets = []
selected = {}

def buttons():
    rows = []
    for asset in otc_assets:
        rows.append([InlineKeyboardButton(
            asset.name,
            callback_data=f"pair:{asset.ric}"
        )])
    if not rows:
        rows = [[InlineKeyboardButton("⚠️ OTC list unavailable", callback_data="noop")]]
    return InlineKeyboardMarkup(rows)

async def init_binomo():
    global api, otc_assets
    if not BINOMO_EMAIL or not BINOMO_PASSWORD:
        log.warning("BINOMO_EMAIL/BINOMO_PASSWORD not configured")
        return
    try:
        login = await asyncio.to_thread(
            BinomoAPI.login, BINOMO_EMAIL, BINOMO_PASSWORD, DEVICE_ID
        )
        api = BinomoAPI.create_from_login(
            login, device_id=DEVICE_ID, demo=True, enable_logging=True
        )
        otc_assets = BinomoAPI.get_otc_assets()
        log.info("Binomo login OK; OTC assets available: %d", len(otc_assets))
        # Connect only to the authenticated WebSocket. No trade execution is enabled.
        await api.connect()
        log.info("Binomo WebSocket connection established")
    except Exception:
        log.exception("Binomo connection failed")
        api = None
        otc_assets = []

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 OTC Live AI\n\n"
        "Binomo OTC connection test is enabled.\n"
        "Select an OTC pair:",
        reply_markup=buttons()
    )

async def pairs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📊 OTC pairs:", reply_markup=buttons())

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if api:
        text = (
            "🟢 Binomo session: CONNECTED\n"
            f"📊 OTC assets loaded: {len(otc_assets)}\n"
            "📡 WebSocket: CONNECTED\n"
            "🚫 Auto-trading: OFF\n\n"
            "Live price/candle decoding will only be shown after "
            "the broker WebSocket message format is verified."
        )
    else:
        text = (
            "🔴 Binomo session: NOT CONNECTED\n\n"
            "Add BINOMO_EMAIL and BINOMO_PASSWORD in Render Environment."
        )
    await update.message.reply_text(text)

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if q.data == "noop":
        return
    ric = q.data.split(":", 1)[1]
    asset = next((a for a in otc_assets if a.ric == ric), None)
    name = asset.name if asset else ric
    selected[q.from_user.id] = ric

    await q.edit_message_text(
        f"📊 {name}\n\n"
        + ("🟢 Binomo WebSocket connected\n" if api else "🔴 Binomo WebSocket not connected\n")
        + "🕯 Live candle: waiting for verified feed decoder\n"
        + "📈 Signal: WAIT\n\n"
        "No random/demo market data is displayed."
    )

async def post_init(application):
    await init_binomo()

async def post_shutdown(application):
    global api
    if api:
        try:
            await api.close()
        except Exception:
            log.exception("Binomo shutdown error")

def main():
    app = (
        Application.builder()
        .token(TOKEN)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("pairs", pairs))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CallbackQueryHandler(button))
    app.run_polling()

if __name__ == "__main__":
    main()
