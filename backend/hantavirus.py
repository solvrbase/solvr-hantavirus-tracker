"""Hantavirus outbreak tracker — live WHO DON RSS parsing + structured response."""
import re
import time
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

_CACHE_TTL = 7200  # 2 hours
_cache: dict = {}

# Baseline from WHO Disease Outbreak News, 2026-05-06.
# These values are overridden at runtime if WHO DON RSS has fresher data.
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
    "source": "WHO Disease Outbreak News",
    "source_url": "https://www.who.int/emergencies/disease-outbreak-news",
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

# ── WHO DON case count parser ─────────────────────────────────────────────────

def _parse_cases(text: str) -> dict:
    """Extract case counts from WHO Disease Outbreak News article text.

    WHO DON articles follow a consistent pattern:
      "As of 6 May, there are 8 cases, 3 of whom are confirmed..."
      "a total of N cases have been identified, of which M are confirmed"
    """
    found: dict = {}
    t = text.replace("\n", " ")

    # Total cases — several common phrasings
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

    # Confirmed
    for pat in [
        r"(\d+)\s+of\s+(?:which|whom)\s+(?:are|were|have\s+been)\s+confirmed",
        r"(\d+)\s+(?:are|were|have\s+been)\s+confirmed\s+by\s+laboratory",
        r"confirmed\s+(?:as\s+)?(?:hantavirus\s+)?(?:by\s+laboratory[^,]*,?\s+)?\s*(\d+)",
    ]:
        m = re.search(pat, t, re.I)
        if m:
            found["confirmed_cases"] = int(m.group(1))
            break

    # Deaths
    m = re.search(r"(\d+)\s+deaths?", t, re.I)
    if m:
        found["deaths"] = int(m.group(1))
    elif re.search(r"no\s+deaths?|without\s+deaths?|zero\s+deaths?", t, re.I):
        found["deaths"] = 0

    return found


def _is_hantavirus_article(article: dict) -> bool:
    text = (article.get("title", "") + " " + article.get("summary", "")).lower()
    return "hantavirus" in text or "hantaviral" in text


# ── Main data function ────────────────────────────────────────────────────────

async def get_hantavirus_data() -> dict:
    """Return structured hantavirus outbreak data. Tries to parse live WHO DON
    case counts from RSS; falls back to hardcoded baseline if unavailable."""
    now = time.time()
    cached = _cache.get("data")
    if cached and (now - cached[1]) < _CACHE_TTL:
        return cached[0]

    # Fetch WHO DON + health news
    news_items: list[dict] = []
    live_counts: dict = {}
    who_article_date: str | None = None

    try:
        from bot.services.news import NewsService
        svc = NewsService()
        try:
            result = await svc.get_headlines("health", limit=50)
        finally:
            await svc.close()

        if result.get("success"):
            all_articles = result.get("articles", [])
            hanta_articles = [a for a in all_articles if _is_hantavirus_article(a)]

            # Parse case counts from most recent matching article
            for article in sorted(hanta_articles, key=lambda x: x.get("published_ts", 0), reverse=True):
                text = article.get("title", "") + " " + article.get("summary", "")
                parsed = _parse_cases(text)
                if parsed:
                    live_counts = parsed
                    who_article_date = article.get("published_at")
                    logger.info(f"Hantavirus live counts from '{article.get('source')}': {parsed}")
                    break

            # News feed: hantavirus articles first, then fall through to health headlines
            for a in hanta_articles[:6]:
                news_items.append({
                    "title": a.get("title"),
                    "url": a.get("url"),
                    "source": a.get("source"),
                    "published_at": a.get("published_at"),
                    "summary": a.get("summary"),
                })

    except Exception as e:
        logger.warning(f"Hantavirus WHO DON fetch failed: {e}")

    # Merge live counts into outbreak dict
    import copy
    outbreak = copy.deepcopy(_BASELINE)

    if live_counts:
        if "total_cases" in live_counts:
            outbreak["total_cases"] = live_counts["total_cases"]
        if "confirmed_cases" in live_counts:
            outbreak["confirmed_cases"] = live_counts["confirmed_cases"]
        if "deaths" in live_counts:
            outbreak["deaths"] = live_counts["deaths"]
        if who_article_date:
            outbreak["last_updated"] = who_article_date
        outbreak["live_data"] = True
        outbreak["data_note"] = "Case counts parsed live from WHO Disease Outbreak News RSS feed"
    else:
        outbreak["data_note"] = "Case counts from WHO DON snapshot (2026-05-06). Live parse unavailable."

    data: dict = {
        "success": True,
        "outbreak": outbreak,
        "news": news_items,
        "fetched_at": datetime.utcnow().isoformat() + "Z",
    }
    _cache["data"] = (data, now)
    return data
