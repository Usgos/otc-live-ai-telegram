# OTC Live AI Telegram Bot v2

Telegram-only bot with an authenticated Binomo session test and OTC asset discovery.

Environment variables:
- BOT_TOKEN
- BINOMO_EMAIL
- BINOMO_PASSWORD
- BINOMO_DEVICE_ID (optional)

No trade execution is included. The bot deliberately does not display fabricated
prices. The Binomo WebSocket protocol must be verified before raw messages are
decoded into live ticks/candles.

