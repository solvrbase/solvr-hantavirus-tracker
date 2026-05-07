"""
Hantavirus API handler — aiohttp route.
Drop this into your aiohttp app and register the route.

Route: GET /api/v1/hantavirus
Auth: none (free public endpoint)
"""

import logging
from aiohttp import web

logger = logging.getLogger(__name__)


def _json(data: dict, status: int = 200) -> web.Response:
    return web.json_response(data, status=status)


def _json_err(msg: str, status: int = 400) -> web.Response:
    return web.json_response({"error": msg}, status=status)


async def handle_hantavirus(request: web.Request) -> web.Response:
    """GET /api/v1/hantavirus — Free real-time hantavirus outbreak tracker.

    Returns WHO outbreak data, affected countries, transmission info, live news.
    No authentication required. Cached 2 hours.
    """
    try:
        from .hantavirus import get_hantavirus_data
        data = await get_hantavirus_data()
        return _json(data)
    except Exception as e:
        logger.error(f"Hantavirus endpoint error: {e}", exc_info=True)
        return _json_err("Internal error fetching outbreak data", 500)


# Register in your aiohttp app:
#
#   from backend.api_handler import handle_hantavirus
#   app.router.add_get("/api/v1/hantavirus", handle_hantavirus)
