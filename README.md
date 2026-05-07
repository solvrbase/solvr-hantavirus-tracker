# ☣ Hantavirus Outbreak Tracker

> Real-time Andes Hantavirus surveillance — WHO case data, affected countries, live news, and free AI agent skill.

**Live demo → [solvrbot.com/hantavirus](https://solvrbot.com/hantavirus)**

![Plague Inc inspired tracker UI](https://media.solvrbot.com/hantavirus-preview.png)

---

## What is this

A free, open-source outbreak tracker for the **2026 Andes Hantavirus** event (origin: MV Hondius cruise ship). It:

- Parses live case counts directly from the **WHO Disease Outbreak News RSS feed**
- Falls back to the last-known WHO baseline if live parse fails
- Serves a structured JSON response useful for AI agents, dashboards, and health monitoring bots
- Powers a Plague Inc-inspired web tracker at [solvrbot.com/hantavirus](https://solvrbot.com/hantavirus)

Built and open-sourced by [Solvr](https://solvrbot.com) — the intelligence layer for the agent economy.

---

## Free API endpoint

No API key, no auth, no rate limits beyond IP fairness:

```bash
curl https://solvrbot.com/api/v1/hantavirus
```

```json
{
  "success": true,
  "outbreak": {
    "name": "Andes Hantavirus",
    "status": "ACTIVE",
    "risk_level": "MODERATE",
    "total_cases": 8,
    "confirmed_cases": 3,
    "deaths": 0,
    "live_data": true,
    "transmission": {
      "person_to_person": true,
      "historical_cfr_pct": 35,
      "incubation_days": "7–56 days"
    },
    "affected": [
      { "name": "MV Hondius", "cases": 8, "status": "ACTIVE" },
      { "name": "Switzerland", "cases": 1, "status": "CONFIRMED" },
      { "name": "Argentina", "status": "SOURCE REGION" }
    ]
  },
  "news": [...],
  "fetched_at": "2026-05-07T..."
}
```

Cached 2 hours. `live_data: true` means case counts were parsed live from WHO DON RSS.

---

## Agent skill.md

Paste this into any AI agent (works with Bankr, OpenClaw, or any skill.md-compatible platform):

```yaml
---
name: hantavirus-tracker
description: Free real-time hantavirus outbreak surveillance. WHO case data,
  affected countries, transmission intel, live news. No auth required.
api: https://solvrbot.com/api/v1/hantavirus
tier: free
---
GET https://solvrbot.com/api/v1/hantavirus
```

Full skill.md: [skill.md](./skill.md)

---

## Fork and deploy your own

The tracker runs on:
- **Frontend**: Next.js 14 — [frontend/page.tsx](./frontend/page.tsx)
- **Backend**: Python aiohttp — [backend/hantavirus.py](./backend/hantavirus.py)
- **API**: Free endpoint at `https://solvrbot.com/api/v1/hantavirus` (no backend needed if you just use ours)

### Fastest path — use our API, deploy only the frontend

1. Fork this repo
2. Drop `frontend/page.tsx` into your Next.js `app/hantavirus/` directory
3. Done — the page calls our free API, no backend setup needed

### Self-host the backend

Requires `httpx` and a news RSS fetcher. See [backend/hantavirus.py](./backend/hantavirus.py) for the service code and [backend/api_handler.py](./backend/api_handler.py) for the aiohttp route.

---

## Data sources

| Data | Source | Freshness |
|------|--------|-----------|
| Case counts | WHO Disease Outbreak News RSS | Live parse (2h cache) |
| Affected regions | WHO DON 2026-05-06 | Manual update as situation evolves |
| News articles | BBC Health, The Guardian Health, WHO DON | 2h cache |
| Transmission info | WHO/CDC Hantavirus fact sheets | Static |

---

## About Solvr

This tracker is powered by the **Solvr Intelligence API** — a free tier API for AI agents that provides world news, WHO outbreak data, global economic data, token security scans, and technical analysis.

- API docs: [solvrbot.com/api-docs](https://solvrbot.com/api-docs)
- Skills library: [solvrbot.com/skills](https://solvrbot.com/skills)
- X: [@solvrbot](https://x.com/solvrbot)

---

*MIT License · Star this if you find it useful ⭐*
