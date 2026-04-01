import logging
import asyncio
import httpx
import random
from typing import List, Optional
from bs4 import BeautifulSoup

from http_client import random_headers
from listing import Listing

logger = logging.getLogger(__name__)

# КОНСТАНТЫ
VINTED_BASE_URL = "https://www.vinted.pl"
VINTED_API_URL = "https://www.vinted.pl/api/v2/catalog/items"

# ОГРАНИЧИТЕЛЬ: Разрешаем максимум 2 одновременных запроса к страницам товаров
# Это спасет от ошибки 429
sem = asyncio.Semaphore(2)

CONDITION_MAP = {
    "1": "Nowy z metką",
    "2": "Nowy bez metki",
    "3": "Bardzo dobry",
    "4": "Dobry",
    "5": "Zadowalający",
    "6": "Do renowacji",
}


async def get_location_from_html(item_url: str, client: httpx.AsyncClient) -> str:
    """
    Безопасно парсит HTML страницы товара с использованием семафора и задержек.
    """
    async with sem:
        try:
            # Рандомная пауза от 2 до 4 секунд, чтобы имитировать человека
            await asyncio.sleep(random.uniform(2.0, 4.0))

            headers = random_headers({"Referer": VINTED_BASE_URL})
            resp = await client.get(item_url, headers=headers, timeout=15.0)

            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, 'html.parser')
                loc_element = soup.find(attrs={"data-testid": "seller-location"})
                if loc_element:
                    return loc_element.get_text(strip=True)
            elif resp.status_code == 429:
                logger.warning(f"⚠️ Vinted выдал 429 (Too Many Requests). Нужно остыть!")
                return "RATE_LIMITED"

        except Exception as e:
            logger.error(f"Ошибка при загрузке HTML {item_url}: {e}")

    return ""


async def process_single_item(item: dict, client: httpx.AsyncClient) -> Optional[Listing]:
    """
    Обрабатывает один айтем: фильтрует по цене/названию и идет за локацией.
    """
    try:
        # 1. ФИЛЬТР ЦЕНЫ
        price_val = float(item.get("price", {}).get("amount", 0))
        if price_val < 850:
            return None

        # 2. ФИЛЬТР ЗАГОЛОВКА
        title = item.get("title", "")
        title_lower = title.lower()
        if "pro" not in title_lower and "max" not in title_lower:
            return None

        # 3. ПОЛУЧЕНИЕ ЛОКАЦИИ (только для прошедших фильтр)
        url = item.get("url", "")
        full_url = url if url.startswith("http") else VINTED_BASE_URL + url

        location_info = await get_location_from_html(full_url, client)

        # Если поймали лимит или локация пустая — скипаем
        if not location_info or location_info == "RATE_LIMITED":
            return None

        # Проверка на Польшу
        if "polska" not in location_info.lower():
            return None

        return Listing(
            id=f"vinted_{item['id']}",
            source="vinted",
            title=title,
            price=f"{price_val} PLN",
            condition=CONDITION_MAP.get(str(item.get("status_id", "")), "Nieznany"),
            url=full_url,
            image_url=item.get("photos", [{}])[0].get("url") if item.get("photos") else None,
            location=location_info,
            seller=item.get("user", {}).get("login"),
        )
    except Exception:
        return None


async def fetch_vinted(query: str, client: httpx.AsyncClient) -> List[Listing]:
    """
    Основная точка входа для поиска Vinted.
    """
    # Проверка сессии
    if not client.cookies.get("vinted_fr_session"):
        try:
            await client.get(VINTED_BASE_URL, headers=random_headers())
            await asyncio.sleep(1)
        except:
            return []

    params = {
        "search_text": query,
        "order": "newest_first",
        "per_page": 40,
        "catalog_ids": "78",
    }

    try:
        headers = random_headers({"X-Requested-With": "XMLHttpRequest"})
        resp = await client.get(VINTED_API_URL, params=params, headers=headers)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        logger.error(f"Vinted API Error: {e}")
        return []

    items = data.get("items", [])
    if not items:
        return []

    # Запускаем задачи параллельно, но под контролем Semaphore
    tasks = [process_single_item(item, client) for item in items]
    results = await asyncio.gather(*tasks)

    final_listings = [r for r in results if r is not None]
    logger.info(f"Vinted: Найдено {len(final_listings)} лотов для '{query}'")

    return final_listings