"""Hantavirus outbreak tracker — standalone Solvr Intel feed parser."""
import re
import time
import asyncio
import logging
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

import httpx

logger = logging.getLogger(__name__)

_CACHE_TTL = 7200  # 2 hours
_cache: dict = {}

_NEWS_FEEDS = [
    ("Solvr Intel", "https://news.google.com/rss/search?q=hantavirus&hl=en-US&gl=US&ceid=US:en"),
    ("Solvr Intel Health", "http://feeds.bbci.co.uk/news/health/rss.xml"),
    ("Solvr Intel Global", "https://www.theguardian.com/society/health/rss"),
]

# Global disease surveillance feeds — Google News RSS (ProMED/HealthMap RSS shut down 2023, WHO DON RSS dead)
_GLOBAL_INTEL_FEEDS = [
    ("Global Health News", "https://news.google.com/rss/search?q=hantavirus&hl=en-US&gl=US&ceid=US:en"),
    ("WHO Outbreak Intel", "https://news.google.com/rss/search?q=hantavirus+WHO+confirmed+cases&hl=en-US&gl=US&ceid=US:en"),
]

_RSS_UA = "HantavirusTracker/1.0 (https://github.com/solvrbase/solvr-hantavirus-tracker)"
_BROWSER_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"

_PROMED_COUNTRY_MAP: dict[str, dict] = {
    "ARGENTINA":        {"id": "AR", "name": "Argentina",     "flag": "🇦🇷", "lat": -35.0,  "lon": -65.0,  "region": "South America"},
    "CHILE":            {"id": "CL", "name": "Chile",         "flag": "🇨🇱", "lat": -33.5,  "lon": -70.7,  "region": "South America"},
    "BRAZIL":           {"id": "BR", "name": "Brazil",        "flag": "🇧🇷", "lat": -14.0,  "lon": -51.0,  "region": "South America"},
    "BOLIVIA":          {"id": "BO", "name": "Bolivia",       "flag": "🇧🇴", "lat": -16.3,  "lon": -63.6,  "region": "South America"},
    "PARAGUAY":         {"id": "PY", "name": "Paraguay",      "flag": "🇵🇾", "lat": -23.4,  "lon": -58.4,  "region": "South America"},
    "URUGUAY":          {"id": "UY", "name": "Uruguay",       "flag": "🇺🇾", "lat": -32.5,  "lon": -55.8,  "region": "South America"},
    "PANAMA":           {"id": "PA", "name": "Panama",        "flag": "🇵🇦", "lat":   8.5,  "lon": -80.8,  "region": "Central America"},
    "VENEZUELA":        {"id": "VE", "name": "Venezuela",     "flag": "🇻🇪", "lat":   8.0,  "lon": -66.0,  "region": "South America"},
    "USA":              {"id": "US", "name": "United States", "flag": "🇺🇸", "lat":  38.0,  "lon": -97.0,  "region": "North America"},
    "UNITED STATES":    {"id": "US", "name": "United States", "flag": "🇺🇸", "lat":  38.0,  "lon": -97.0,  "region": "North America"},
    "CANADA":           {"id": "CA", "name": "Canada",        "flag": "🇨🇦", "lat":  56.0,  "lon": -96.0,  "region": "North America"},
    "GERMANY":          {"id": "DE", "name": "Germany",       "flag": "🇩🇪", "lat":  51.0,  "lon":  10.0,  "region": "Europe"},
    "FINLAND":          {"id": "FI", "name": "Finland",       "flag": "🇫🇮", "lat":  61.0,  "lon":  26.0,  "region": "Europe"},
    "SWEDEN":           {"id": "SE", "name": "Sweden",        "flag": "🇸🇪", "lat":  62.0,  "lon":  15.0,  "region": "Europe"},
    "FRANCE":           {"id": "FR", "name": "France",        "flag": "🇫🇷", "lat":  46.0,  "lon":   2.0,  "region": "Europe"},
    "SWITZERLAND":      {"id": "CH", "name": "Switzerland",   "flag": "🇨🇭", "lat":  47.0,  "lon":   8.0,  "region": "Europe"},
    "RUSSIA":           {"id": "RU", "name": "Russia",        "flag": "🇷🇺", "lat":  60.0,  "lon": 100.0,  "region": "Europe/Asia"},
    "CHINA":            {"id": "CN", "name": "China",         "flag": "🇨🇳", "lat":  35.0,  "lon": 105.0,  "region": "Asia"},
    "SOUTH KOREA":      {"id": "KR", "name": "South Korea",   "flag": "🇰🇷", "lat":  37.0,  "lon": 127.5,  "region": "Asia"},
    "REPUBLIC OF KOREA":{"id": "KR", "name": "South Korea",   "flag": "🇰🇷", "lat":  37.0,  "lon": 127.5,  "region": "Asia"},
    "JAPAN":            {"id": "JP", "name": "Japan",         "flag": "🇯🇵", "lat":  36.0,  "lon": 138.0,  "region": "Asia"},
    "SENEGAL":          {"id": "SN", "name": "Senegal",       "flag": "🇸🇳", "lat":  14.0,  "lon": -14.0,  "region": "Africa"},
    "SOUTH AFRICA":     {"id": "ZA", "name": "South Africa",  "flag": "🇿🇦", "lat": -30.0,  "lon":  25.0,  "region": "Africa"},
}


def _strip_html(html: str) -> str:
    """Strip scripts, styles, tags and unescape common HTML entities."""
    text = re.sub(r"(?s)<script[^>]*?>.*?</script>", " ", html)
    text = re.sub(r"(?s)<style[^>]*?>.*?</style>", " ", text)
    text = re.sub(r"<[^>]+>", " ", text)
    for ent, val in [("&nbsp;", " "), ("&#160;", " "), ("&amp;", "&"),
                     ("&lt;", "<"), ("&gt;", ">"), ("&quot;", '"')]:
        text = text.replace(ent, val)
    return re.sub(r"\s+", " ", text).strip()


async def _fetch_article_text(client: httpx.AsyncClient, url: str) -> str:
    """Fetch an article URL, return stripped plain text (capped at 12KB)."""
    try:
        r = await client.get(url, timeout=8)
        r.raise_for_status()
        return _strip_html(r.text)[:12000]
    except Exception:
        return ""


async def _scrape_who_don(client: httpx.AsyncClient) -> dict:
    """Scrape WHO Disease Outbreak News listing for hantavirus DON pages.
    Returns parsed case counts, or empty dict on failure."""
    try:
        r = await client.get(
            "https://www.who.int/emergencies/disease-outbreak-news",
            timeout=12,
            headers={"User-Agent": _BROWSER_UA},
        )
        r.raise_for_status()
        html = r.text
        don_urls: list[str] = []
        for m in re.finditer(r'href="(/emergencies/disease-outbreak-news/item/[^"]+)"', html):
            path = m.group(1)
            idx = html.find(path)
            context = html[max(0, idx - 300):idx + 400]
            if "hantavirus" in context.lower():
                full_url = "https://www.who.int" + path
                if full_url not in don_urls:
                    don_urls.append(full_url)
        if not don_urls:
            logger.debug("WHO DON: no hantavirus entries on listing page")
            return {}
        for url in don_urls[:3]:
            try:
                dr = await client.get(url, timeout=10, headers={"User-Agent": _BROWSER_UA})
                dr.raise_for_status()
                parsed = _parse_cases(_strip_html(dr.text))
                if parsed:
                    parsed["source_url"] = url
                    logger.info(f"WHO DON parsed: {parsed} from {url}")
                    return parsed
            except Exception as e:
                logger.debug(f"WHO DON page failed ({url}): {e}")
        return {}
    except Exception as e:
        logger.warning(f"WHO DON scrape failed: {e}")
        return {}


def _parse_promed_location(title: str) -> dict | None:
    """Extract country from a ProMED title like 'HANTAVIRUS, HUMAN - ARGENTINA: (TUCUMAN)'."""
    m = re.search(r"HANTAVIRUS[^-]*-\s*([A-Z][A-Z\s]+?)(?:\s*[:(,]|\s*$)", title, re.I)
    if not m:
        return None
    return _PROMED_COUNTRY_MAP.get(m.group(1).strip().upper())

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
    "global_confirmed_baseline": 159,
    "global_confirmed_baseline_date": "2026-05-08",
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
        r"total\s+of\s+(\d+)\s+(?:human\s+)?(?:hantavirus\s+)?cases?",
        r"(\d+)\s+(?:human\s+)?(?:hantavirus\s+)?cases?\s+(?:have\s+been\s+)?(?:identified|reported|detected|confirmed)",
        r"(\d+)\s+(?:human\s+)?(?:hantavirus\s+)?cases?\s+including",
        r"(\d+)\s+cases?,\s+\d+\s+of\s+(?:which|whom)",
        r"there\s+are\s+(\d+)\s+(?:hantavirus\s+)?cases?",
        r"(\d+)\s+cases?\s+of\s+(?:hantavirus|hps\b|hvps\b)",
        r"confirmed\s+(\d+)\s+(?:hantavirus\s+)?cases?",
        r"(?:reported|affecting)\s+(\d+)\s+(?:people|persons|individuals|patients)",
    ]:
        m = re.search(pat, t, re.I)
        if m:
            found["total_cases"] = int(m.group(1))
            break

    for pat in [
        r"(\d+)\s+of\s+(?:which|whom)\s+(?:are|were|have\s+been)\s+confirmed",
        r"(\d+)\s+(?:are|were|have\s+been)\s+confirmed\s+by\s+laboratory",
        r"(\d+)\s+laboratory[- ]confirmed",
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
    global_intel: list[dict] = []
    live_counts: dict = {}
    who_article_date: str | None = None
    who_don_counts: dict = {}

    async def _fetch_cluster_feeds() -> None:
        try:
            async with httpx.AsyncClient(headers={"User-Agent": _RSS_UA}, follow_redirects=True) as client:
                results = await asyncio.gather(
                    *[_fetch_rss(client, n, u) for n, u in _NEWS_FEEDS],
                    return_exceptions=True,
                )
            all_cluster: list[dict] = []
            for r in results:
                if isinstance(r, list):
                    all_cluster.extend(r)
            hanta_articles = [a for a in all_cluster if _is_hantavirus(a["title"], a["summary"])]
            for article in hanta_articles:
                text = article["title"] + " " + article["summary"]
                parsed = _parse_cases(text)
                if parsed:
                    nonlocal live_counts, who_article_date
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
            logger.warning(f"Cluster feeds failed: {e}")

    async def _fetch_global_feeds() -> None:
        try:
            async with httpx.AsyncClient(headers={"User-Agent": _RSS_UA}, follow_redirects=True) as client:
                results = await asyncio.gather(
                    *[_fetch_rss(client, n, u) for n, u in _GLOBAL_INTEL_FEEDS],
                    return_exceptions=True,
                )
            for r in results:
                if isinstance(r, list):
                    for a in r:
                        if _is_hantavirus(a["title"], a["summary"]):
                            global_intel.append({
                                "title": a["title"],
                                "url": a["url"],
                                "source": a["source"],
                                "published_at": a["published_at"],
                                "summary": a["summary"],
                            })
        except Exception as e:
            logger.warning(f"Global intel feeds failed: {e}")

    async def _fetch_who_don() -> None:
        nonlocal who_don_counts
        try:
            async with httpx.AsyncClient(follow_redirects=True) as client:
                who_don_counts = await _scrape_who_don(client)
        except Exception as e:
            logger.warning(f"WHO DON task failed: {e}")

    # Phase 1: RSS feeds + WHO DON scrape in parallel
    await asyncio.gather(_fetch_cluster_feeds(), _fetch_global_feeds(), _fetch_who_don())

    # Phase 2: parse case counts from RSS snippet text
    global_confirmed: int | None = None
    global_confirmed_date: str | None = None
    for article in news_items + global_intel:
        text = (article.get("title") or "") + " " + (article.get("summary") or "")
        parsed = _parse_cases(text)
        n = parsed.get("total_cases")
        if n and (global_confirmed is None or n > global_confirmed):
            global_confirmed = n
            global_confirmed_date = article.get("published_at")

    # Phase 3: fetch full article text for deeper parsing
    all_urls = list({a["url"] for a in (news_items + global_intel) if a.get("url")})
    if all_urls:
        try:
            async with httpx.AsyncClient(
                headers={"User-Agent": _BROWSER_UA},
                follow_redirects=True,
                max_redirects=5,
            ) as client:
                texts = await asyncio.gather(
                    *[_fetch_article_text(client, u) for u in all_urls[:8]],
                    return_exceptions=True,
                )
            for text in texts:
                if not isinstance(text, str) or not text:
                    continue
                if "hantavirus" not in text.lower():
                    continue
                parsed = _parse_cases(text)
                n = parsed.get("total_cases")
                if n and (global_confirmed is None or n > global_confirmed):
                    global_confirmed = n
                    logger.info(f"Global count updated from full article text: {n}")
                if not live_counts and parsed.get("total_cases", 0) >= _BASELINE["total_cases"]:
                    live_counts = parsed
                    logger.info(f"Cluster counts updated from full article text: {parsed}")
        except Exception as e:
            logger.warning(f"Article text deep-fetch failed: {e}")

    # Phase 4: WHO DON scraped counts as final override
    if who_don_counts:
        n = who_don_counts.get("total_cases")
        if n and (global_confirmed is None or n > global_confirmed):
            global_confirmed = n
            logger.info(f"Global count updated from WHO DON: {n}")
        if not live_counts and who_don_counts.get("total_cases"):
            live_counts = who_don_counts

    import copy
    outbreak = copy.deepcopy(_BASELINE)

    if live_counts:
        for key in ("total_cases", "confirmed_cases", "deaths"):
            if key in live_counts:
                outbreak[key] = live_counts[key]
        if who_article_date:
            outbreak["last_updated"] = who_article_date
        outbreak["live_data"] = True
        outbreak["data_note"] = "Case counts parsed live from article text"
    else:
        outbreak["data_note"] = "Case counts from Solvr Hantavirus Tracker Skill snapshot (2026-05-06). Live parse unavailable."

    # Merge news-article-detected country mentions into affected regions
    existing_ids = {a["id"] for a in outbreak["affected"]}
    for article in global_intel:
        loc = _parse_promed_location(article.get("title", ""))
        if not loc or loc["id"] in existing_ids:
            continue
        existing_ids.add(loc["id"])
        outbreak["affected"].append({
            "id": loc["id"],
            "name": loc["name"],
            "region": loc["region"],
            "flag": loc["flag"],
            "lat": loc["lat"],
            "lon": loc["lon"],
            "cases": None,
            "confirmed": None,
            "deaths": None,
            "status": "REPORTED",
            "detail": f"Reported in news: {article['title'][:140]}",
        })

    data: dict = {
        "success": True,
        "outbreak": outbreak,
        "news": news_items,
        "global_intel": global_intel[:12],
        "global_confirmed": global_confirmed or _BASELINE["global_confirmed_baseline"],
        "global_confirmed_date": global_confirmed_date or _BASELINE["global_confirmed_baseline_date"],
        "global_confirmed_live": global_confirmed is not None,
        "fetched_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
    _cache["data"] = (data, now)
    return data
