from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Listing:
    id: str                          # unique ID used for deduplication
    source: str                      # "olx" | "allegro" | "vinted"
    title: str
    price: Optional[str]
    condition: Optional[str]
    url: str
    image_url: Optional[str] = None
    location: Optional[str] = None
    seller: Optional[str] = None
    description: Optional[str] = None
    extra: dict = field(default_factory=dict)  # any extra source-specific fields
