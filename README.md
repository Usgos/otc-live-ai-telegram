# OTC Live AI — Telegram Bot

This is a Telegram-only bot skeleton for a verified live OTC-data integration.

## Required environment variable
`BOT_TOKEN` = the token from BotFather.

## Important
The bot intentionally does **not** generate fake/random market data.
The live Binomo OTC adapter must be connected and tested before displaying
live prices, candles, or CALL/PUT analysis.

## Render
This repository is configured as a Render worker using `render.yaml`.
