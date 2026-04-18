"""Person 2 module: lightweight portfolio URL scraper."""

from __future__ import annotations

import re

import requests


TAG_RE = re.compile(r"<[^>]+>")
WS_RE = re.compile(r"\s+")


def scrape_portfolio_text(url: str, max_chars: int = 5000) -> str:
    """Fetch and clean visible-ish text from a portfolio URL."""
    try:
        res = requests.get(url, timeout=10)
        if res.status_code != 200:
            return ""

        html = res.text
        html = re.sub(r"(?is)<script.*?>.*?</script>", " ", html)
        html = re.sub(r"(?is)<style.*?>.*?</style>", " ", html)
        text = TAG_RE.sub(" ", html)
        text = WS_RE.sub(" ", text).strip()
        return text[:max_chars]
    except Exception:
        return ""
