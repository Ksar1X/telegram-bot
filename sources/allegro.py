import logging
import urllib.parse
from typing import List

import httpx
from bs4 import BeautifulSoup

from http_client import random_headers, random_delay
from listing import Listing

logger = logging.getLogger(__name__)

ALLEGRO_SEARCH_URL = "https://allegro.pl/listing"


async def fetch_allegro(query: str, client: httpx.AsyncClient) -> List[Listing]:
    """
    Scrape Allegro search results page.
    Allegro renders listings in JSON inside a <script type='application/json'> tag.
    """
    params = {
        "string": query,
        "order": "n",   # newest first
        "bmatch": "baseline-product-cl-eyesa2-engag-dict45-ele-1-2-0312",
    }
    url = f"{ALLEGRO_SEARCH_URL}?" + urllib.parse.urlencode(params)
    headers = random_headers({
        "Referer": "https://allegro.pl/",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "pl-PL,pl;q=0.9",
    })

    try:
        await random_delay()
        resp = await client.get(url, headers=headers)
        resp.raise_for_status()
        html = resp.text
    except Exception as e:
        logger.error(f"Allegro fetch error for '{query}': {e}")
        return []

    listings: List[Listing] = []
    try:
        soup = BeautifulSoup(html, "html.parser")

        # Allegro embeds listing data as JSON in <script data-box-name="items container">
        # or as a regular script block with __listing_StoreState
        script_tag = soup.find("script", {"data-box-name": "items container"})

        if not script_tag:
            # fallback: look for JSON-LD or any article tags
            articles = soup.find_all("article", attrs={"data-analytics-view-value": True})
            for article in articles:
                try:
                    listing_id = f"allegro_{article.get('data-analytics-view-value', '')}"
                    a_tag = article.find("a", href=True)
                    title_tag = article.find("h2") or article.find("a")
                    title = title_tag.get_text(strip=True) if title_tag else "Brak tytułu"
                    link = a_tag["href"] if a_tag else ""
                    if link and not link.startswith("http"):
                        link = "https://allegro.pl" + link

                    price_tag = article.find(attrs={"data-testid": "price-value"}) or article.find(class_=lambda c: c and "price" in c.lower())
                    price = price_tag.get_text(strip=True) if price_tag else None

                    img_tag = article.find("img")
                    image_url = img_tag.get("src") or img_tag.get("data-src") if img_tag else None

                    listings.append(Listing(
                        id=listing_id,
                        source="allegro",
                        title=title,
                        price=price,
                        condition=None,
                        url=link,
                        image_url=image_url,
                    ))
                except Exception as inner:
                    logger.warning(f"Allegro: failed to parse article: {inner}")
                    continue
        else:
            import json
            data = json.loads(script_tag.string or "{}")
            items = (
                data.get("props", {})
                    .get("pageProps", {})
                    .get("dehydratedState", {})
                    .get("queries", [{}])[0]
                    .get("state", {})
                    .get("data", {})
                    .get("items", {})
                    .get("normalizedItems", [])
            )
            for item in items:
                try:
                    listing_id = f"allegro_{item.get('id', '')}"
                    title = item.get("name", "")
                    slug = item.get("slug", "")
                    item_id = item.get("id", "")
                    link = f"https://allegro.pl/oferta/{slug}-{item_id}" if slug else ""

                    price_obj = item.get("sellingMode", {}).get("price", {})
                    price = f"{price_obj.get('amount', '')} {price_obj.get('currency', 'PLN')}".strip() or None

                    images = item.get("images", [])
                    image_url = images[0].get("url") if images else None

                    condition = item.get("condition", None)

                    listings.append(Listing(
                        id=listing_id,
                        source="allegro",
                        title=title,
                        price=price,
                        condition=condition,
                        url=link,
                        image_url=image_url,
                    ))
                except Exception as inner:
                    logger.warning(f"Allegro JSON: failed to parse item: {inner}")
                    continue

    except Exception as e:
        logger.error(f"Allegro parse error for '{query}': {e}")
        return []

    logger.info(f"Allegro: found {len(listings)} listings for '{query}'")
    return listings
