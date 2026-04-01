import logging
from typing import Optional

import httpx

from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from listing import Listing

logger = logging.getLogger(__name__)

TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

SOURCE_LABELS = {
    "olx": "🟠 OLX",
    "allegro": "🔴 Allegro",
    "vinted": "🟢 Vinted",
}


def _format_message(listing: Listing) -> str:
    source_label = SOURCE_LABELS.get(listing.source, listing.source.upper())
    lines = [
        f"{source_label}",
        f"",
        f"📱 <b>{listing.title}</b>",
    ]

    if listing.price:
        lines.append(f"💰 <b>Cena:</b> {listing.price}")
    else:
        lines.append("💰 <b>Cena:</b> brak danych")

    if listing.condition:
        lines.append(f"📦 <b>Stan:</b> {listing.condition}")

    if listing.location:
        lines.append(f"📍 <b>Lokalizacja:</b> {listing.location}")

    if listing.seller:
        lines.append(f"👤 <b>Sprzedający:</b> {listing.seller}")

    if listing.description:
        desc = listing.description[:300] + "…" if len(listing.description) > 300 else listing.description
        lines.append(f"\n📝 {desc}")

    lines.append(f"\n🔗 <a href='{listing.url}'>Zobacz ogłoszenie</a>")

    return "\n".join(lines)


async def send_listing(listing: Listing, client: httpx.AsyncClient):
    text = _format_message(listing)

    if listing.image_url:
        await _send_photo(listing.image_url, text, client)
    else:
        await _send_text(text, client)


async def _send_photo(image_url: str, caption: str, client: httpx.AsyncClient):
    try:
        resp = await client.post(
            f"{TELEGRAM_API}/sendPhoto",
            json={
                "chat_id": TELEGRAM_CHAT_ID,
                "photo": image_url,
                "caption": caption,
                "parse_mode": "HTML",
            },
        )
        if not resp.is_success:
            logger.warning(f"sendPhoto failed ({resp.status_code}), falling back to text")
            await _send_text(caption, client)
    except Exception as e:
        logger.error(f"send_photo error: {e}")
        await _send_text(caption, client)


async def _send_text(text: str, client: httpx.AsyncClient):
    try:
        resp = await client.post(
            f"{TELEGRAM_API}/sendMessage",
            json={
                "chat_id": TELEGRAM_CHAT_ID,
                "text": text,
                "parse_mode": "HTML",
                "disable_web_page_preview": False,
            },
        )
        resp.raise_for_status()
    except Exception as e:
        logger.error(f"send_text error: {e}")


async def send_plain(text: str, client: httpx.AsyncClient):
    """Send a plain text message (for /start, /stop confirmations etc.)."""
    try:
        resp = await client.post(
            f"{TELEGRAM_API}/sendMessage",
            json={
                "chat_id": TELEGRAM_CHAT_ID,
                "text": text,
                "parse_mode": "HTML",
            },
        )
        resp.raise_for_status()
    except Exception as e:
        logger.error(f"send_plain error: {e}")
