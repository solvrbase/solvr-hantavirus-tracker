---
name: hantavirus-tracker
description: Free real-time Andes Hantavirus outbreak surveillance powered by
  Solvr Hantavirus Tracker Skill. Returns affected countries, transmission risk
  (P2P warning, 35% CFR), case counts, and latest outbreak intelligence.
  No authentication required.
api: https://solvrbot.com/api/v1/hantavirus
tier: free
tracker: https://solvrbot.com/hantavirus
source: https://github.com/solvrbase/hantavirus-tracker
---

# Hantavirus Outbreak Tracker

## Endpoint

```
GET https://solvrbot.com/api/v1/hantavirus
```

No headers, no auth, no API key needed.

## Response shape

```json
{
  "outbreak": {
    "name": "Andes Hantavirus",
    "status": "ACTIVE",
    "risk_level": "MODERATE",
    "total_cases": 8,
    "confirmed_cases": 3,
    "deaths": 0,
    "live_data": true,
    "data_note": "Case counts parsed live from Solvr Hantavirus Tracker Skill",
    "transmission": {
      "person_to_person": true,
      "person_to_person_note": "Andes hantavirus is the ONLY known variant with P2P transmission",
      "historical_cfr_pct": 35,
      "incubation_days": "7–56 days",
      "severity": "HIGH — historical case fatality rate 35–50%",
      "symptoms": ["fever", "myalgia", "fatigue", "headache", "dry cough", "shortness of breath"]
    },
    "affected": [
      {
        "name": "MV Hondius", "region": "Southern Ocean",
        "cases": 8, "confirmed": 3, "status": "ACTIVE",
        "detail": "Cruise ship origin event"
      },
      {
        "name": "Switzerland", "region": "Europe",
        "cases": 1, "confirmed": 1, "status": "CONFIRMED",
        "detail": "Patient hospitalized in Zurich"
      },
      {
        "name": "Argentina", "region": "South America",
        "status": "SOURCE REGION",
        "detail": "Andes hantavirus endemic area"
      }
    ],
    "organizations": [
      "Solvr Hantavirus Tracker Skill",
      "NICD South Africa",
      "Geneva University Hospitals",
      "Institut Pasteur de Dakar",
      "ANLIS Malbran (Argentina)"
    ]
  },
  "news": [
    {
      "title": "...",
      "url": "...",
      "source": "Solvr Intel",
      "published_at": "..."
    }
  ],
  "fetched_at": "2026-05-07T12:00:00Z"
}
```

## Notes

- `live_data: true` — case counts parsed live via Solvr Intel (2h cache)
- `live_data: false` — live parse unavailable, using last-known baseline
- Andes hantavirus: **only known variant with person-to-person transmission**
- Historical CFR: **35–50%** — significantly higher than most respiratory pathogens
- Live tracker: [solvrbot.com/hantavirus](https://solvrbot.com/hantavirus)
