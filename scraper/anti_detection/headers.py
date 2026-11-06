"""Realistic HTTP header generator for avoiding bot detection."""

from __future__ import annotations

import random
from typing import Dict, Optional
from scraper.anti_detection.user_agents import get_random_user_agent

ACCEPT_LANGUAGES = [
    "en-US,en;q=0.9",
    "en-GB,en;q=0.9,en-US;q=0.8",
    "en-US,en;q=0.9,fr;q=0.8",
    "en-CA,en;q=0.9,en;q=0.8",
]


def generate_realistic_headers(
    user_agent: Optional[str] = None,
    referer: Optional[str] = None
) -> Dict[str, str]:
    """Generate modern, browser-like request headers."""
    ua = user_agent or get_random_user_agent("desktop")

    is_chrome = "Chrome" in ua and "Edg" not in ua
    is_firefox = "Firefox" in ua
    is_safari = "Safari" in ua and "Chrome" not in ua

    headers = {
        "User-Agent": ua,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": random.choice(ACCEPT_LANGUAGES),
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }

    if is_chrome:
        headers.update({
            "Sec-Ch-Ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"macOS"' if "Mac" in ua else '"Windows"',
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
        })
    elif is_firefox:
        headers.update({
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
        })

    if referer:
        headers["Referer"] = referer

    return headers
