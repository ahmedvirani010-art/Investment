This is a [Next.js](https://nextjs.org) project bootstrapped with [`create-next-app`](https://nextjs.org/docs/app/api-reference/cli/create-next-app).

## Environment variables

Create a `.env` file in the project root. Optional variables:

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | Prisma database URL (e.g. SQLite `file:./dev.db`). |
| `CRON_SECRET` | Secret for cron endpoints (e.g. `/api/cron/sync-prices`). If set, requests must send `Authorization: Bearer <CRON_SECRET>` or `?secret=<CRON_SECRET>`. |
| `BRACKLY_API_KEY` | Optional. API key for [Brackly Capital](https://capital.brackly.com) to fetch PSX prices for symbols that fail on Yahoo. Register at [capital.brackly.com/api-register](https://capital.brackly.com/api-register). When set, "Refresh prices" will use Brackly as fallback for those symbols. |

**Price fallbacks when Yahoo fails:** The app tries, in order: Yahoo → Brackly (if key set) → PSX portal scrape → **local price store** (`price_data/prices.db`). To fill the local store (e.g. for symbols that Yahoo doesn’t return), run the Python price store so it fetches and saves data: from the project root run `python psx_price_store.py` (or call `bulk_update` with your symbol list). Then "Refresh prices" will use the latest close from that DB for any symbol that still has no price from Yahoo/Brackly/PSX.
| `PYTHON_PATH` | Path to Python (e.g. `py` on Windows, `python3` on Linux/Mac). Used by analysis routes. |

**HMM Regime Analysis:** For true Hidden Markov Model (hmmlearn), use Python 3.11 or 3.12 and install in order: see [docs/HMM_SETUP.md](docs/HMM_SETUP.md).

## Troubleshooting: Connection refused

- **Browser shows "Connection refused" when opening the app**  
  The Next.js dev server is not running. Start it with `npm run dev` (or `yarn dev` / `pnpm dev`) and open [http://localhost:3000](http://localhost:3000). If the app runs on a different port (e.g. 3001), use that port in the URL.

- **Connection refused when running Technical Analysis (or other analysis that uses the LLM)**  
  The technical agent can call OpenRouter for the AI summary. If your network or firewall blocks outbound HTTPS to `openrouter.ai`, the Python process may get "Connection refused" or a similar error. The app falls back to rule-based summary when the LLM fails; if you see the error in the UI, check that OpenRouter is reachable or disable LLM usage. Ensure no proxy is misconfigured for localhost or for the Python process.

- **Database "Connection refused"**  
  This project uses SQLite by default (`DATABASE_URL=file:./dev.db`), which does not use the network. If you switched to PostgreSQL or another TCP datasource, ensure the database server is running and that `DATABASE_URL` in `.env` is correct (host, port, and credentials).

## Getting Started

First, run the development server:

```bash
npm run dev
# or
yarn dev
# or
pnpm dev
# or
bun dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser to see the result.

You can start editing the page by modifying `app/page.tsx`. The page auto-updates as you edit the file.

This project uses [`next/font`](https://nextjs.org/docs/app/building-your-application/optimizing/fonts) to automatically optimize and load [Geist](https://vercel.com/font), a new font family for Vercel.

## Learn More

To learn more about Next.js, take a look at the following resources:

- [Next.js Documentation](https://nextjs.org/docs) - learn about Next.js features and API.
- [Learn Next.js](https://nextjs.org/learn) - an interactive Next.js tutorial.

You can check out [the Next.js GitHub repository](https://github.com/vercel/next.js) - your feedback and contributions are welcome!

## Deploy on Vercel

The easiest way to deploy your Next.js app is to use the [Vercel Platform](https://vercel.com/new?utm_medium=default-template&filter=next.js&utm_source=create-next-app&utm_campaign=create-next-app-readme) from the creators of Next.js.

Check out our [Next.js deployment documentation](https://nextjs.org/docs/app/building-your-application/deploying) for more details.
