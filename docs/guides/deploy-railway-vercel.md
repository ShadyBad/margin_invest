# Deploy Margin Invest to Railway + Vercel

## Prerequisites

- [Railway](https://railway.app) account (free trial includes $5 credit)
- [Vercel](https://vercel.com) account (free hobby tier)
- GitHub repo pushed with latest code
- Local dev environment with `uv` installed

---

## Part 1: Create the Railway Project

1. Go to [railway.app/new](https://railway.app/new)
2. Click **Empty Project**
3. You'll see an empty project canvas. This is where you'll add three services: PostgreSQL, Redis, and the API.

---

## Part 2: Add PostgreSQL

1. On the project canvas, click the **+ New** button (top right)
2. Click **Database** > **Add PostgreSQL**
3. A PostgreSQL card appears on the canvas. Wait ~30 seconds for it to provision.
4. Click the PostgreSQL card to open it
5. Click the **Data** tab — you should see an empty database. This confirms it's running.
6. Click the **Variables** tab — you'll see auto-generated variables like `PGUSER`, `POSTGRES_PASSWORD`, `PGDATABASE`, `DATABASE_URL`, etc.
7. You don't need to copy anything yet — Railway lets the API service reference these variables directly.

> Railway PostgreSQL does NOT include TimescaleDB. This is fine — the Alembic migration checks for it and skips gracefully if absent.

---

## Part 3: Add Redis

1. Click the **+ New** button again (top right of project canvas)
2. Click **Database** > **Add Redis**
3. A Redis card appears on the canvas. Wait for it to provision.
4. You don't need to copy anything yet.

---

## Part 4: Deploy the API Service

### 4.1 Connect your GitHub repo

1. Click the **+ New** button again (top right of project canvas)
2. Click **GitHub Repo**
3. Select your Margin Invest repository from the list
4. A new service card appears on the canvas — this is your API service
5. Railway detects `railway.toml` and will start building from `api/Dockerfile`
6. **The first deploy will likely fail** because the database has no tables yet. That's expected.

### 4.2 Add environment variables to the API service

1. Click the **API service card** on the canvas (the GitHub repo one — NOT the PostgreSQL or Redis cards)
2. Click the **Variables** tab
3. Click **+ New Variable** for each of the following. Add them one at a time:

**Database connection** — tells the API how to reach PostgreSQL:
```
Variable: MARGIN_DATABASE_URL
Value:    postgresql+asyncpg://${{Postgres.PGUSER}}:${{Postgres.POSTGRES_PASSWORD}}@${{Postgres.RAILWAY_PRIVATE_DOMAIN}}:5432/${{Postgres.PGDATABASE}}?sslmode=require
```
> The `${{Postgres.XXX}}` syntax is Railway's variable referencing. When you type `${{`, Railway shows an autocomplete dropdown. Select the Postgres service, then the variable. Railway resolves these at deploy time.

**Redis connection** — tells the API how to reach Redis:
```
Variable: MARGIN_REDIS_URL
Value:    ${{Redis.REDIS_URL}}
```
> Same referencing pattern. Type `${{`, select the Redis service, select `REDIS_URL`.

**Environment flag** — activates production guards:
```
Variable: MARGIN_ENVIRONMENT
Value:    production
```

**CORS** — which frontend domains can call the API:
```
Variable: MARGIN_CORS_ORIGINS
Value:    ["http://localhost:3000"]
```
> Set this to localhost for now. You'll update it to your Vercel URL in Part 7.

**JWT secret** — used for auth tokens. Generate this in your terminal:
```bash
openssl rand -hex 32
```
```
Variable: MARGIN_JWT_SECRET
Value:    (paste the output from the command above)
```

**API key encryption** — encrypts stored API keys. Generate a Fernet key in your terminal:
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```
```
Variable: MARGIN_API_KEY_ENCRYPTION_KEY
Value:    (paste the output from the command above)
```

**MFA encryption** — encrypts TOTP secrets. Generate ANOTHER Fernet key (do NOT reuse the one above):
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```
```
Variable: MARGIN_MFA_ENCRYPTION_KEY
Value:    (paste the output from the command above)
```

**WebAuthn** — for passkey authentication:
```
Variable: MARGIN_WEBAUTHN_RP_ID
Value:    localhost

Variable: MARGIN_WEBAUTHN_RP_ORIGIN
Value:    http://localhost:3000
```
> Set these to localhost for now. You'll update them to your Vercel domain in Part 7.

### 4.3 Generate a public URL for the API

1. Still on the API service card, click **Settings**
2. Scroll to the **Networking** section
3. Click **Generate Domain** — Railway assigns a URL like `margin-invest-production.up.railway.app`
4. **Save this URL** — you'll need it for the frontend config and for testing

### 4.4 Redeploy

After adding all variables, Railway should automatically redeploy. If it doesn't:
1. Click the **Deployments** tab on the API service card
2. Click **Redeploy** on the latest deployment

The deploy will still fail if migrations haven't been run — proceed to Part 5.

---

## Part 5: Run Migrations & Seed Data

These commands run on **your local machine** against the cloud database. The Docker image doesn't include Alembic migration files.

### 5.1 Get the external database connection string

You need the **public-facing** PostgreSQL URL (your laptop can't reach Railway's private network).

1. Go back to your Railway project canvas
2. Click the **PostgreSQL card** (not the API service)
3. Click the **Variables** tab
4. Find `DATABASE_URL` — it looks like:
   ```
   postgresql://postgres:abc123@roundhouse.proxy.rlwy.net:54321/railway
   ```
5. Copy it and convert it for asyncpg. Make two changes:
   - Replace `postgresql://` with `postgresql+asyncpg://`
   - Add `?sslmode=require` at the end

   Example result:
   ```
   postgresql+asyncpg://postgres:abc123@roundhouse.proxy.rlwy.net:54321/railway?sslmode=require
   ```

### 5.2 Set the URL in your terminal

```bash
export MARGIN_DATABASE_URL="postgresql+asyncpg://postgres:abc123@roundhouse.proxy.rlwy.net:54321/railway?sslmode=require"
```
> Replace the example values with your actual PostgreSQL credentials from step 5.1.

### 5.3 Run migrations

```bash
uv run alembic -c api/alembic.ini upgrade head
```

You should see output like:
```
INFO  [alembic.runtime.migration] Running upgrade  -> 4ee2f8646129, initial schema
INFO  [alembic.runtime.migration] Running upgrade 4ee2f8646129 -> ...
...
```

### 5.4 Seed initial data

```bash
uv run python -m margin_api.cli seed --tickers AAPL MSFT NVDA GOOGL AMZN META TSLA
```

This fetches financial data from yfinance and stores it in the cloud database. Takes 1-2 minutes.

### 5.5 Score the seeded tickers

```bash
uv run python -m margin_api.cli score --tickers AAPL MSFT NVDA GOOGL AMZN META TSLA
```

### 5.6 Verify the API is working

Use the public URL from step 4.3:

```bash
curl https://your-api.up.railway.app/health
# Expected: {"status":"ok"}

curl https://your-api.up.railway.app/api/v1/scores
# Expected: JSON array with scored tickers
```

---

## Part 6: Deploy the Frontend to Vercel

### 6.1 Import the project

1. Go to [vercel.com/new](https://vercel.com/new)
2. Click **Import Git Repository** and select your Margin Invest repo
3. Vercel asks for project settings:
   - **Root Directory**: Click **Edit** and set to `web`
   - **Framework Preset**: Should auto-detect **Next.js**
4. **Don't click Deploy yet** — add environment variables first (next step)

### 6.2 Add environment variables

On the same setup page, scroll to **Environment Variables** and add each one:

**API URL (public)** — used by browser-side code:
```
Variable: NEXT_PUBLIC_API_URL
Value:    https://your-api.up.railway.app
```
> Use the Railway public URL from step 4.3.

**API URL (server-side)** — used by Next.js API routes:
```
Variable: API_URL
Value:    https://your-api.up.railway.app
```
> Same URL. This one stays private on the server.

**Auth secret** — used by NextAuth.js. Generate in your terminal:
```bash
openssl rand -hex 32
```
```
Variable: AUTH_SECRET
Value:    (paste the output)
```

**OAuth providers** (optional — skip if you don't have OAuth set up yet):
```
Variable: GOOGLE_CLIENT_ID
Value:    (from Google Cloud Console)

Variable: GOOGLE_CLIENT_SECRET
Value:    (from Google Cloud Console)

Variable: GITHUB_CLIENT_ID
Value:    (from GitHub Developer Settings)

Variable: GITHUB_CLIENT_SECRET
Value:    (from GitHub Developer Settings)
```

### 6.3 Deploy

Click **Deploy**. Vercel builds the Next.js app. When done, it assigns a URL like `margin-invest.vercel.app`.

**Save this URL** — you need it for the next step.

---

## Part 7: Update Railway with the Vercel URL

Now that you have the Vercel frontend URL, go back to Railway and update three variables on the **API service** (not the PostgreSQL card):

1. Click the API service card > **Variables** tab
2. Find and update these three variables:

```
MARGIN_CORS_ORIGINS         →  ["https://margin-invest.vercel.app"]
MARGIN_WEBAUTHN_RP_ID       →  margin-invest.vercel.app
MARGIN_WEBAUTHN_RP_ORIGIN   →  https://margin-invest.vercel.app
```
> Replace `margin-invest.vercel.app` with your actual Vercel URL.

Railway auto-redeploys when you save the variables.

---

## Part 8: Verify End-to-End

1. Open your Vercel URL in a browser
2. The dashboard should load and display scored stocks
3. Click a stock card to see the score detail panel
4. If OAuth is configured, test the sign-in flow

---

## Cost Estimate

| Service | Cost |
|---|---|
| Railway API container | ~$2-5/mo |
| Railway PostgreSQL (1GB) | ~$5/mo |
| Railway Redis | ~$2/mo |
| Vercel (hobby) | Free |
| **Total** | **~$5-12/mo** (covered by Railway's $5 free trial initially) |

## Scaling Up

### More tickers
The full 3,056-ticker universe needs ~2GB+ in PostgreSQL. Seed in batches:
```bash
uv run python -m margin_api.cli seed --tickers $(head -100 tickers.txt | tr '\n' ' ')
```

### Intraday price data
If you enable the `PriceIntraday` pipeline (5-min OHLCV bars), storage grows ~20MB/day. Consider:
- [Timescale Cloud](https://www.timescale.com/cloud) ($25/mo) for hypertable compression (10-15x)
- Point `MARGIN_DATABASE_URL` at Timescale Cloud instead of Railway PostgreSQL

### Background worker (ARQ)
For automatic scoring, add a second Railway service:
1. Click **+ New** > **GitHub Repo** > select the same Margin Invest repo
2. Go to its **Settings** tab > **Deploy** section
3. Override the start command: `python -m margin_api.worker`
4. Add the same env vars as the API service (it needs DB + Redis access)

## Troubleshooting

**API returns 500 on startup**
- Click the API service card > **Deployments** tab > click the failed deployment > **View Logs**. Most likely `MARGIN_DATABASE_URL` is wrong or migrations haven't been run.

**"MARGIN_DATABASE_URL points to a local address in production mode"**
- The connection string contains `localhost`, `127.0.0.1`, or `0.0.0.0`. Use the Railway URL instead.

**asyncpg SSL errors**
- Make sure `?sslmode=require` is at the end of `MARGIN_DATABASE_URL`. The app auto-creates an SSL context when it sees this parameter.

**asyncpg "prepared statement" errors with PgBouncer**
- If using Supabase or another service that defaults to PgBouncer (transaction pooling mode), use the **direct/session** connection on port 5432 instead of the pooled connection on port 6543. asyncpg uses prepared statements which are incompatible with PgBouncer in transaction mode.

**Migrations fail on "CREATE EXTENSION timescaledb"**
- This shouldn't happen — the migration checks for the extension first. If it does fail, the migration file is `api/alembic/versions/a60167c570ed_add_timeseries_and_backtest_tables.py`. The `has_timescale` check should skip the DDL.
