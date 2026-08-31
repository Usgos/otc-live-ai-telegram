# Quotex OTC Live AI — Telegram Bot v3

The market-data source is Quotex, not Binomo.

The bot is Telegram-only for the user and does not place trades.
It attempts to authenticate to Quotex, discover available instruments,
filter OTC assets, and verify the WebSocket connection.

Environment variables:
- BOT_TOKEN
- QUOTEX_EMAIL
- QUOTEX_PASSWORD
- QUOTEX_SSID (preferred if available; keep private)

Important:
This uses an unofficial third-party Quotex client. It is not affiliated
with Quotex. Verify the live feed before relying on any signal.
No random/demo market data is generated.

