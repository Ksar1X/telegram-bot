import asyncio
import logging
from typing import List

import httpx

from config import SEARCH_QUERIES, POLL_INTERVAL_SECONDS
from db import is_seen, mark_seen, get_alerts_enabled
from http_client import get_client
from listing import Listing
from notifier import send_listing
from sources.olx import fetch_olx
from sources.allegro import fetch_allegro
from sources.vinted import fetch_vinted

logger = logging.getLogger(__name__)


async def poll_once(client: httpx.AsyncClient):
    if not get_alerts_enabled():
        logger.info("Alerts are disabled — skipping poll.")
        return

    all_new: List[Listing] = []

    for query in SEARCH_QUERIES:
        logger.info(f"Polling for: {query}")

        for fetcher, source_name in [
            (fetch_olx, "OLX"),
            (fetch_allegro, "Allegro"),
            (fetch_vinted, "Vinted"),
        ]:
            try:
                results = await fetcher(query, client)
                for listing in results:
                    if not is_seen(listing.id):
                        all_new.append(listing)
                        mark_seen(listing.id, listing.source)
            except Exception as e:
                logger.error(f"{source_name} error for '{query}': {e}")

    logger.info(f"Poll complete — {len(all_new)} new listing(s) found.")

    for listing in all_new:
        await send_listing(listing, client)
        await asyncio.sleep(0.5)  # small gap between Telegram messages


async def run_scheduler():
    """Main loop: poll once, wait POLL_INTERVAL_SECONDS, repeat."""
    async with await get_client() as client:
        while True:
            try:
                await poll_once(client)
            except Exception as e:
                logger.error(f"Unhandled error in poll cycle: {e}")
            logger.info(f"Next poll in {POLL_INTERVAL_SECONDS}s…")
            await asyncio.sleep(POLL_INTERVAL_SECONDS)
