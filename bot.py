import asyncio
import logging
import sys

import httpx

from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from db import init_db, get_alerts_enabled, set_alerts_enabled
from notifier import send_plain
from scheduler import run_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("bot.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"
ALLOWED_CHAT_ID = str(TELEGRAM_CHAT_ID)


async def handle_update(update: dict, client: httpx.AsyncClient):
    message = update.get("message") or update.get("edited_message")
    if not message:
        return

    chat_id = str(message.get("chat", {}).get("id", ""))
    text = (message.get("text") or "").strip().lower()

    # Only respond to the authorised chat
    if chat_id != ALLOWED_CHAT_ID:
        logger.warning(f"Ignored message from unknown chat_id={chat_id}")
        return

    if text in ("/start", "/start@" + (await _get_bot_username(client)).lower()):
        set_alerts_enabled(True)
        await send_plain("✅ <b>Оповещения включены.</b>\nБуду присылать тебе новые оповещения с OLX, Allegro i Vinted.", client)
        logger.info("Alerts enabled by user command.")

    elif text in ("/stop", "/stop@" + (await _get_bot_username(client)).lower()):
        set_alerts_enabled(False)
        await send_plain("🔕 <b>Оповещения выключены.</b>\nНе буду присылать тебе новые оповещегния. Напиши /start, чтобы получать их.", client)
        logger.info("Alerts disabled by user command.")

    elif text == "/status":
        enabled = get_alerts_enabled()
        status = "✅ Включено" if enabled else "🔕 Выключено"
        await send_plain(f"ℹ️ Оповещения сейчас: <b>{status}</b>", client)


_bot_username_cache = None

async def _get_bot_username(client: httpx.AsyncClient) -> str:
    global _bot_username_cache
    if _bot_username_cache:
        return _bot_username_cache
    try:
        resp = await client.get(f"{TELEGRAM_API}/getMe")
        data = resp.json()
        _bot_username_cache = data.get("result", {}).get("username", "")
    except Exception:
        _bot_username_cache = ""
    return _bot_username_cache


async def poll_telegram_updates(client: httpx.AsyncClient):
    """Long-polling loop for Telegram commands."""
    offset = 0
    while True:
        try:
            resp = await client.get(
                f"{TELEGRAM_API}/getUpdates",
                params={"offset": offset, "timeout": 30, "allowed_updates": ["message"]},
                timeout=httpx.Timeout(40.0),
            )
            if resp.is_success:
                updates = resp.json().get("result", [])
                for update in updates:
                    await handle_update(update, client)
                    offset = update["update_id"] + 1
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error(f"Telegram polling error: {e}")
            await asyncio.sleep(5)


async def main():
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN is not set. Please fill in your .env file.")
        sys.exit(1)
    if not TELEGRAM_CHAT_ID:
        logger.error("TELEGRAM_CHAT_ID is not set. Please fill in your .env file.")
        sys.exit(1)

    init_db()
    logger.info("iPhone Listings Bot starting…")

    async with httpx.AsyncClient(
        timeout=httpx.Timeout(40.0),
        follow_redirects=True,
    ) as client:
        await send_plain("🤖 <b>Бот работает!</b>\nМониторю OLX, Allegro i Vinted в поиске iPhone'ов.\nИспользуй /stop чтобы выключить уведомления.", client)

        # Run both loops concurrently
        await asyncio.gather(
            poll_telegram_updates(client),
            run_scheduler(),
        )


if __name__ == "__main__":
    asyncio.run(main())
