import logging
from typing import List

import httpx

from http_client import random_headers, random_delay
from listing import Listing

logger = logging.getLogger(__name__)

VINTED_API_URL = "https://www.vinted.pl/api/v2/catalog/items"

CONDITION_MAP = {
    "1": "Nowy z metką",
    "2": "Nowy bez metki",
    "3": "Bardzo dobry",
    "4": "Dobry",
    "5": "Zadowalający",
    "6": "Do renowacji",
}


async def fetch_vinted(query: str, client: httpx.AsyncClient) -> List[Listing]:
    """
    Query Vinted's internal catalog API.
    This endpoint is unauthenticated but requires browser-like headers.
    """
    params = {
        "search_text": query,
        "order": "newest_first",
        "per_page": 40,
        "page": 1,
        "catalog_ids": "",   # all categories
    }
    headers = random_headers({
        "Referer": "https://www.vinted.pl/catalog",
        "Accept": "application/json, text/plain, */*",
        "X-Requested-With": "XMLHttpRequest",
    })

    try:
        await random_delay()
        resp = await client.get(VINTED_API_URL, params=params, headers=headers)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        logger.error(f"Vinted fetch error for '{query}': {e}")
        return []

    listings: List[Listing] = []
    for item in data.get("items", []):
        try:
            listing_id = f"vinted_{item['id']}"
            title = item.get("title", "")
            url = item.get("url", "")
            if url and not url.startswith("http"):
                url = "https://www.vinted.pl" + url

            # Price
            price_num = item.get("price")
            currency = item.get("currency", "PLN")
            price = f"{price_num} {currency}" if price_num else None

            # Condition
            condition_id = str(item.get("status_id", ""))
            condition = CONDITION_MAP.get(condition_id)

            # Image
            photos = item.get("photos", [])
            image_url = None
            if photos:
                image_url = (
                    photos[0].get("full_size_url")
                    or photos[0].get("url")
                    or photos[0].get("thumbnails", [{}])[-1].get("url")
                )

            # Seller
            user = item.get("user", {})
            seller = user.get("login") or None

            listings.append(Listing(
                id=listing_id,
                source="vinted",
                title=title,
                price=price,
                condition=condition,
                url=url,
                image_url=image_url,
                seller=seller,
            ))
        except Exception as e:
            logger.warning(f"Vinted: failed to parse item: {e}")
            continue

    logger.info(f"Vinted: found {len(listings)} listings for '{query}'")
    return listings
