import os
import asyncio
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from pyquotex.api import QuotexAPI

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("quotex-otc-bot")

BOT_TOKEN = os.getenv("BOT_TOKEN")
QX_EMAIL = os.getenv("QUOTEX_EMAIL")
QX_PASSWORD = os.getenv("QUOTEX_PASSWORD")
QX_SSID = os.getenv("QUOTEX_SSID")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is missing")

api = None
connected = False
assets = []

def asset_name(a):
    if isinstance(a, dict):
        return a.get("name") or a.get("symbol") or a.get("asset") or str(a)
    return getattr(a, "name", None) or getattr(a, "symbol", None) or str(a)

def asset_symbol(a):
    if isinstance(a, dict):
        return a.get("symbol") or a.get("asset") or a.get("name")
    return getattr(a, "symbol", None) or getattr(a, "name", None) or str(a)

def is_otc(a):
    s = asset_symbol(a) or ""
    return "_otc" in str(s).lower() or "otc" in asset_name(a).lower()

def keyboard():
    otc = [a for a in assets if is_otc(a)]
    if not otc:
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 Refresh", callback_data="refresh")]
        ])
    rows = [
        [InlineKeyboardButton(asset_name(a), callback_data=f"pair:{asset_symbol(a)}")]
        for a in otc[:50]
    ]
    rows.append([InlineKeyboardButton("🔄 Refresh", callback_data="refresh")])
    return InlineKeyboardMarkup(rows)

async def connect_quotex():
    global api, connected, assets

    if not QX_EMAIL and not QX_SSID:
        log.warning("QUOTEX_EMAIL/QUOTEX_SSID not configured")
        return

    try:
        # The upstream client supports email/password login and SSID sessions.
        # No order/trading method is called here.
        api = QuotexAPI(
            host="quotex.market",
            username=QX_EMAIL or "",
            password=QX_PASSWORD or "",
            lang="en",
        )

        if QX_SSID:
            api.set_ssid = QX_SSID

        ok, reason = await api.start_websocket()
        if not ok:
            raise RuntimeError(reason)

        if QX_SSID:
            await api.send_ssid()
        else:
            # start_websocket authenticates with configured email/password.
            pass

        await asyncio.sleep(1)
        await api.get_instruments()
        await asyncio.sleep(2)

        assets = list(getattr(api, "instruments", []) or [])
        connected = True
        log.info("Quotex connected; instruments=%d; OTC=%d",
                 len(assets), sum(is_otc(a) for a in assets))
    except Exception:
        connected = False
        assets = []
        log.exception("Quotex connection failed")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📊 Quotex OTC Live AI\n\n"
        "Source: Quotex\n"
        "Auto-trading: OFF\n\n"
        "Select an available OTC pair:",
        reply_markup=keyboard(),
    )

async def pairs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📊 Quotex OTC pairs:",
        reply_markup=keyboard(),
    )

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    otc_count = sum(is_otc(a) for a in assets)
    await update.message.reply_text(
        f"{'🟢' if connected else '🔴'} Quotex connection: "
        f"{'CONNECTED' if connected else 'NOT CONNECTED'}\n"
        f"📊 Instruments: {len(assets)}\n"
        f"📈 OTC instruments: {otc_count}\n"
        "🚫 Auto-trading: OFF\n"
        "🕯 Live candle decoder: next step after connection verification."
    )

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global assets
    q = update.callback_query
    await q.answer()

    if q.data == "refresh":
        await connect_quotex()
        await q.edit_message_text(
            "📊 Quotex OTC pairs:",
            reply_markup=keyboard()
        )
        return

    symbol = q.data.split(":", 1)[1]
    await q.edit_message_text(
        f"📊 {symbol}\n\n"
        f"{'🟢 Quotex WebSocket connected' if connected else '🔴 Quotex not connected'}\n"
        "🕯 Live candle: waiting for verified stream\n"
        "📈 Signal: WAIT\n\n"
        "No random/fake market data is displayed."
    )

async def post_init(app):
    await connect_quotex()

async def post_shutdown(app):
    global api
    if api:
        try:
            await api.close()
        except Exception:
            pass

def main():
    app = (
        Application.builder()
        .token(BOT_TOKEN)
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
