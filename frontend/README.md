# Frontend — Next.js 14

Drop `page.tsx` into your Next.js app at `app/hantavirus/page.tsx`.

## Requirements

```bash
npm install viem          # already in most Next.js projects
```

The page calls `GET /api/v1/hantavirus` (relative URL). If you're not running
the backend, change the `API_URL` constant to point at the Solvr API directly:

```ts
// page.tsx line 4
const API_URL = "https://solvrbot.com/api/v1/hantavirus";
```

No other changes needed. The full UI runs client-side with no additional deps.
