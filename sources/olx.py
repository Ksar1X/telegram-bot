import logging
from typing import List

import httpx

from http_client import random_headers, random_delay
from listing import Listing

logger = logging.getLogger(__name__)

OLX_API_URL = "https://www.olx.pl/api/v1/offers/"

CONDITION_MAP = {
    "new": "Nowy",
    "used": "Używany",
}


async def fetch_olx(query: str, client: httpx.AsyncClient) -> List[Listing]:
    """
    Query OLX's internal JSON API for a search term.
    Returns a list of Listing objects.
    """
    params = {
        "offset": 0,
        "limit": 40,
        "query": query,
        "category_id": 1306,  # Telefony i Akcesoria > Telefony komórkowe
        "sort_by": "created_at:desc",
    }
    headers = random_headers({
        "Referer": "https://www.olx.pl/elektronika/telefony/",
        "Accept": "application/json",
    })

    try:
        await random_delay()
        resp = await client.get(OLX_API_URL, params=params, headers=headers)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        logger.error(f"OLX fetch error for '{query}': {e}")
        return []

    listings: List[Listing] = []
    for item in data.get("data", []):
        try:
            listing_id = f"olx_{item['id']}"
            title = item.get("title", "")
            url = item.get("url", "")

            # Price
            price_data = item.get("price", {})
            price = None
            if price_data:
                value = price_data.get("value")
                currency = price_data.get("currency", "PLN")
                if value is not None:
                    price = f"{value} {currency}"
                elif price_data.get("label"):
                    price = price_data["label"]

            # Location
            location_data = item.get("location", {})
            city = location_data.get("city", {}).get("name", "")
            region = location_data.get("region", {}).get("name", "")
            location = ", ".join(filter(None, [city, region])) or None

            # Image
            photos = item.get("photos", [])
            image_url = photos[0].get("link", "").replace("{width}", "400").replace("{height}", "400") if photos else None

            # Condition from params
            condition = None
            for param in item.get("params", []):
                if param.get("key") == "state":
                    condition = param.get("value", {}).get("label")
                    break

            # Seller
            user = item.get("user", {})
            seller = user.get("name") or None

            listings.append(Listing(
                id=listing_id,
                source="olx",
                title=title,
                price=price,
                condition=condition,
                url=url,
                image_url=image_url,
                location=location,
                seller=seller,
            ))
        except Exception as e:
            logger.warning(f"OLX: failed to parse item: {e}")
            continue

    logger.info(f"OLX: found {len(listings)} listings for '{query}'")
    return listings
