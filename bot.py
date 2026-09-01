import os
import asyncio
import logging

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

from pyquotex.api import QuotexAPI

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

log = logging.getLogger("otc-bot")

BOT_TOKEN = os.getenv("BOT_TOKEN")
QX_EMAIL = os.getenv("QUOTEX_EMAIL")
QX_PASSWORD = os.getenv("QUOTEX_PASSWORD")

api = None
connected = False
assets = []
last_login_attempt = 0


def is_otc(asset):
    text = str(asset).lower()

    if isinstance(asset, dict):
        text = " ".join(
            str(asset.get(k, ""))
            for k in ("name", "symbol", "asset")
        ).lower()

    return "otc" in text


def asset_name(asset):
    if isinstance(asset, dict):
        return (
            asset.get("name")
            or asset.get("symbol")
            or asset.get("asset")
            or "Unknown"
        )

    return (
        getattr(asset, "name", None)
        or getattr(asset, "symbol", None)
        or str(asset)
    )


def asset_symbol(asset):
    if isinstance(asset, dict):
        return (
            asset.get("symbol")
            or asset.get("asset")
            or asset.get("name")
        )

    return (
        getattr(asset, "symbol", None)
        or getattr(asset, "name", None)
        or str(asset)
    )


def pair_keyboard():
    otc = [a for a in assets if is_otc(a)]

    rows = []

    for asset in otc[:50]:
        symbol = asset_symbol(asset)

        rows.append([
            InlineKeyboardButton(
                asset_name(asset),
                callback_data=f"pair:{symbol}"
            )
        ])

    if not rows:
        rows.append([
            InlineKeyboardButton(
                "🔄 Refresh",
                callback_data="refresh"
            )
        ])

    return InlineKeyboardMarkup(rows)


async def connect_quotex():
    global api
    global connected
    global assets
    global last_login_attempt

    if connected:
        return True

    if not QX_EMAIL or not QX_PASSWORD:
        log.warning(
            "QUOTEX_EMAIL or QUOTEX_PASSWORD missing"
        )
        return False

    # Don't repeatedly hit the login endpoint.
    now = asyncio.get_running_loop().time()

    if now - last_login_attempt < 300:
        log.warning(
            "Login cooldown active. Not retrying yet."
        )
        return False

    last_login_attempt = now

    try:
        log.info("Starting Quotex connection...")

        api = QuotexAPI(
            host="quotex.market",
            username=QX_EMAIL,
            password=QX_PASSWORD,
            lang="en",
        )

        ok, reason = await api.start_websocket()

        if not ok:
            raise RuntimeError(str(reason))

        await asyncio.sleep(2)

        await api.get_instruments()

        await asyncio.sleep(2)

        instruments = getattr(
            api,
            "instruments",
            []
        )

        assets = list(instruments or [])

        connected = True

        otc_count = sum(
            1 for a in assets if is_otc(a)
        )

        log.info(
            "Quotex connected | instruments=%d | OTC=%d",
            len(assets),
            otc_count
        )

        return True

    except Exception as exc:
        connected = False
        assets = []

        log.error(
            "Quotex connection failed: %s",
            exc
        )

        return False


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📊 Quotex OTC Live AI\n\n"
        "Source: Quotex\n"
        "Auto-trading: OFF\n\n"
        "Live market data will only be shown "
        "after the Quotex connection is verified.",
        reply_markup=pair_keyboard()
    )


async def pairs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📊 Quotex OTC Pairs",
        reply_markup=pair_keyboard()
    )


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    otc_count = sum(
        1 for a in assets if is_otc(a)
    )

    await update.message.reply_text(
        f"{'🟢' if connected else '🔴'} "
        f"Quotex: "
        f"{'CONNECTED' if connected else 'NOT CONNECTED'}\n\n"
        f"📊 Instruments: {len(assets)}\n"
        f"📈 OTC instruments: {otc_count}\n"
        f"🚫 Auto-trading: OFF\n"
        f"🕯 Live candle: NOT ENABLED YET"
    )


async def refresh(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()

    ok = await connect_quotex()

    if ok:
        text = (
            "🟢 Quotex connected\n\n"
            "OTC pairs loaded."
        )
    else:
        text = (
            "🔴 Quotex connection not available.\n\n"
            "The bot will not repeatedly retry login."
        )

    await update.callback_query.edit_message_text(
        text,
        reply_markup=pair_keyboard()
    )


async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    await query.answer()

    if query.data == "refresh":
        await refresh(update, context)
        return

    symbol = query.data.split(":", 1)[1]

    await query.edit_message_text(
        f"📊 {symbol}\n\n"
        f"{'🟢 Quotex connected' if connected else '🔴 Quotex disconnected'}\n\n"
        "🕯 Candle: waiting for verified live stream\n"
        "📈 Signal: WAIT\n\n"
        "No random/demo price is being generated."
    )


async def post_init(application):
    await connect_quotex()


async def post_shutdown(application):
    global api

    if api:
        try:
            await api.close()
        except Exception:
            pass


def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN is missing")

    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )

    application.add_handler(
        CommandHandler("start", start)
    )

    application.add_handler(
        CommandHandler("pairs", pairs)
    )

    application.add_handler(
        CommandHandler("status", status)
    )

    application.add_handler(
        CallbackQueryHandler(button)
    )

    application.run_polling()


if __name__ == "__main__":
    main()
