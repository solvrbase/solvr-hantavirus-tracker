"""Hantavirus outbreak tracker — standalone Solvr Intel feed parser."""
import re
import time
import logging
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

import httpx

logger = logging.getLogger(__name__)

_CACHE_TTL = 7200  # 2 hours
_cache: dict = {}

_SOLVR_INTEL_RSS = "https://www.who.int/feeds/entity/csr/don/en/rss.xml"

_NEWS_FEEDS = [
    ("Solvr Hantavirus Tracker Skill", _SOLVR_INTEL_RSS),
    ("Solvr Intel Health", "http://feeds.bbci.co.uk/news/health/rss.xml"),
    ("Solvr Intel Global", "https://www.theguardian.com/society/health/rss"),
]

_BASELINE = {
    "name": "Andes Hantavirus",
    "subtype": "HPS — Hantavirus Pulmonary Syndrome",
    "origin_event": "MV Hondius cruise ship",
    "status": "ACTIVE",
    "risk_level": "MODERATE",
    "who_global_risk": "LOW",
    "total_cases": 8,
    "confirmed_cases": 3,
    "deaths": 0,
    "first_detected": "2026-04",
    "last_updated": "2026-05-06",
    "source": "Solvr Hantavirus Tracker Skill",
    "source_url": "https://solvrbot.com/hantavirus",
    "live_data": False,
    "transmission": {
        "type": "Zoonotic (rodent-borne)",
        "vector": "Andes deer mouse — Oligoryzomys longicaudatus",
        "person_to_person": True,
        "person_to_person_note": "Andes hantavirus is the ONLY known hantavirus variant capable of person-to-person transmission",
        "incubation_days": "7–56 days (1–8 weeks)",
        "historical_cfr_pct": 35,
        "severity": "HIGH — historical case fatality rate 35–50%",
        "symptoms": ["fever", "myalgia", "fatigue", "headache", "dry cough", "shortness of breath"],
    },
    "affected": [
        {
            "id": "vessel",
            "name": "MV Hondius",
            "region": "Southern Ocean",
            "flag": "🚢",
            "lat": -60.0,
            "lon": -55.0,
            "cases": 8,
            "confirmed": 3,
            "deaths": 0,
            "status": "ACTIVE",
            "detail": "Cruise ship origin event; all passengers and crew under contact tracing",
        },
        {
            "id": "CH",
            "name": "Switzerland",
            "region": "Europe",
            "flag": "🇨🇭",
            "lat": 47.0,
            "lon": 8.0,
            "cases": 1,
            "confirmed": 1,
            "deaths": 0,
            "status": "CONFIRMED",
            "detail": "Patient hospitalized in Zurich; receiving care at Geneva University Hospitals network",
        },
        {
            "id": "AR",
            "name": "Argentina",
            "region": "South America",
            "flag": "🇦🇷",
            "lat": -35.0,
            "lon": -65.0,
            "cases": None,
            "confirmed": None,
            "deaths": 0,
            "status": "SOURCE REGION",
            "detail": "Andes hantavirus endemic area; ANLIS Malbran providing diagnostics and epidemiological support",
        },
        {
            "id": "ZA",
            "name": "South Africa",
            "region": "Africa",
            "flag": "🇿🇦",
            "lat": -30.0,
            "lon": 25.0,
            "cases": None,
            "confirmed": None,
            "deaths": 0,
            "status": "RESPONDING",
            "detail": "NICD providing advanced laboratory diagnostics and molecular confirmation",
        },
        {
            "id": "SN",
            "name": "Senegal",
            "region": "Africa",
            "flag": "🇸🇳",
            "lat": 14.0,
            "lon": -14.0,
            "cases": None,
            "confirmed": None,
            "deaths": 0,
            "status": "RESPONDING",
            "detail": "Institut Pasteur de Dakar supporting international contact tracing operations",
        },
    ],
    "organizations": [
        "World Health Organization (WHO)",
        "NICD — National Institute for Communicable Diseases (South Africa)",
        "Geneva University Hospitals (Switzerland)",
        "Institut Pasteur de Dakar (Senegal)",
        "ANLIS Malbran (Argentina)",
    ],
}


def _parse_cases(text: str) -> dict:
    found: dict = {}
    t = text.replace("\n", " ")

    for pat in [
        r"total\s+of\s+(\d+)\s+(?:human\s+)?cases?",
        r"there\s+are\s+(\d+)\s+cases?",
        r"(\d+)\s+cases?,\s+\d+\s+of\s+whom",
        r"(\d+)\s+(?:human\s+)?cases?\s+(?:have\s+been\s+)?(?:identified|reported|detected|confirmed)",
        r"(\d+)\s+(?:human\s+)?cases?\s+including",
    ]:
        m = re.search(pat, t, re.I)
        if m:
            found["total_cases"] = int(m.group(1))
            break

    for pat in [
        r"(\d+)\s+of\s+(?:which|whom)\s+(?:are|were|have\s+been)\s+confirmed",
        r"(\d+)\s+(?:are|were|have\s+been)\s+confirmed\s+by\s+laboratory",
        r"confirmed\s+(?:as\s+)?(?:hantavirus\s+)?(?:by\s+laboratory[^,]*,?\s+)?\s*(\d+)",
    ]:
        m = re.search(pat, t, re.I)
        if m:
            found["confirmed_cases"] = int(m.group(1))
            break

    m = re.search(r"(\d+)\s+deaths?", t, re.I)
    if m:
        found["deaths"] = int(m.group(1))
    elif re.search(r"no\s+deaths?|without\s+deaths?|zero\s+deaths?", t, re.I):
        found["deaths"] = 0

    return found


def _is_hantavirus(title: str, summary: str) -> bool:
    text = (title + " " + summary).lower()
    return "hantavirus" in text or "hantaviral" in text


async def _fetch_rss(client: httpx.AsyncClient, name: str, url: str) -> list[dict]:
    """Fetch and parse a single RSS feed. Returns list of article dicts."""
    try:
        r = await client.get(url, timeout=10)
        r.raise_for_status()
        root = ET.fromstring(r.text)
        items = []
        for item in root.iter("item"):
            title = item.findtext("title", "").strip()
            link = item.findtext("link", "").strip()
            desc = item.findtext("description", "").strip()
            pub = item.findtext("pubDate", "").strip()
            items.append({
                "title": title,
                "url": link,
                "source": name,
                "published_at": pub,
                "summary": re.sub(r"<[^>]+>", "", desc)[:500],
            })
        return items
    except Exception as e:
        logger.warning(f"RSS fetch failed ({name}): {e}")
        return []


async def get_hantavirus_data() -> dict:
    """Return structured hantavirus outbreak data.
    Fetches live intel feed; falls back to hardcoded baseline if unavailable.
    """
    now = time.time()
    cached = _cache.get("data")
    if cached and (now - cached[1]) < _CACHE_TTL:
        return cached[0]

    news_items: list[dict] = []
    live_counts: dict = {}
    who_article_date: str | None = None

    try:
        async with httpx.AsyncClient(
            headers={"User-Agent": "HantavirusTracker/1.0 (https://github.com/solvrbase/solvr-hantavirus-tracker)"},
            follow_redirects=True,
        ) as client:
            all_articles: list[dict] = []
            for feed_name, feed_url in _NEWS_FEEDS:
                articles = await _fetch_rss(client, feed_name, feed_url)
                all_articles.extend(articles)

        hanta_articles = [a for a in all_articles if _is_hantavirus(a["title"], a["summary"])]

        for article in hanta_articles:
            text = article["title"] + " " + article["summary"]
            parsed = _parse_cases(text)
            if parsed:
                live_counts = parsed
                who_article_date = article.get("published_at")
                break

        for a in hanta_articles[:6]:
            news_items.append({
                "title": a["title"],
                "url": a["url"],
                "source": "Solvr Intel",
                "published_at": a["published_at"],
                "summary": a["summary"],
            })

    except Exception as e:
        logger.warning(f"RSS pipeline failed: {e}")

    import copy
    outbreak = copy.deepcopy(_BASELINE)

    if live_counts:
        for key in ("total_cases", "confirmed_cases", "deaths"):
            if key in live_counts:
                outbreak[key] = live_counts[key]
        if who_article_date:
            outbreak["last_updated"] = who_article_date
        outbreak["live_data"] = True
        outbreak["data_note"] = "Case counts parsed live from Solvr Hantavirus Tracker Skill"
    else:
        outbreak["data_note"] = "Case counts from Solvr Hantavirus Tracker Skill snapshot (2026-05-06). Live parse unavailable."

    data: dict = {
        "success": True,
        "outbreak": outbreak,
        "news": news_items,
        "fetched_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
    _cache["data"] = (data, now)
    return data
