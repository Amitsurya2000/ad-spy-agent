# Deploying Ad Spy Agent (Hetzner, fully self-hosted)

```
One Hetzner Cloud VPS, everything via Docker Compose:

Caddy (HTTPS, reverse proxy)
  /            -> web (Next.js dashboard)
  /images/*    -> static files off the shared ad_images volume

web      - Next.js dashboard + API routes + Gemini rewrite/clone/niche-transform
worker   - Python + Chromium, scrapes the Facebook Ad Library
postgres - the only datastore, reachable only inside the Docker network
```

> **Why a real Chromium worker at all:** the scraper drives a stealthy
> browser session against `facebook.com/ads/library` for tens of seconds to
> minutes per job - that's exactly what a normal container process (unlike a
> serverless function) is fine at. Because the worker and dashboard now run
> on the same box, ad screenshots need no upload step either: the worker
> just writes them to a shared disk volume and Caddy serves that directory
> directly.

## 1. Create the server

1. [Hetzner Cloud Console](https://console.hetzner.cloud) -> New Server.
2. Image: **Ubuntu 24.04**. Any shared vCPU plan (CX22 or similar) is enough
   for this workload.
3. Add your SSH key, create the server, note its public IPv4.
4. Point a domain (or subdomain) at that IP: an **A record** ->
   `adspy.yourdomain.com` -> the server's IP. Caddy needs this to be live
   before it can request a Let's Encrypt certificate.

## 2. Install Docker

```bash
ssh root@<server-ip>
apt update && apt upgrade -y
curl -fsSL https://get.docker.com | sh
```

(The `docker compose` plugin comes bundled with that install script.)

## 3. Deploy

```bash
git clone https://github.com/Amitsurya2000/ad-spy-agent.git
cd ad-spy-agent
cp .env.example .env
nano .env   # fill in POSTGRES_PASSWORD, GEMINI_API_KEY, DASHBOARD_PASSWORD, DOMAIN

docker compose up -d --build
```

That builds and starts all four containers. First build is slow (Chromium +
OS libs for the worker); later builds are cached. `db/schema.sql` runs
automatically the first time the `postgres` volume is created.

Visit `https://<DOMAIN>` - Caddy provisions HTTPS automatically. You'll get
a browser Basic Auth prompt if `DASHBOARD_PASSWORD` is set.

## 4. Updating later

```bash
git pull
docker compose up -d --build
```

## Notes

- **Facebook may still block/CAPTCHA a datacenter IP** (Hetzner included) -
  this was true on the previous Oracle deployment too. If scraping gets
  blocked consistently, point the worker's outbound traffic through a
  residential proxy, or run `worker.py` from a home connection instead (see
  "Local development" below for running it outside Docker) while keeping
  the dashboard + Postgres on the Hetzner box.
- **Backups:** `docker compose exec postgres pg_dump -U adspy adspy >
  backup.sql` covers the database; the `ad_images` volume holds the
  screenshots. Neither is backed up automatically - set up a cron job if
  you care about keeping history.
- **Logs:** `docker compose logs -f worker` (or `web`, `caddy`, `postgres`).
- Rotate `POSTGRES_PASSWORD`/`DASHBOARD_PASSWORD` in `.env` and
  `docker compose up -d` to apply changes.

## Local development (without Docker)

**Dashboard:**
```bash
cd web
cp .env.example .env.local   # point DATABASE_URL at a local/dev Postgres
npm install
npm run dev
```

**Worker** (needs Chromium installed once, and a Postgres it can reach - the
same one the dashboard is pointed at, with `db/schema.sql` applied):
```bash
python -m venv venv
./venv/Scripts/python.exe -m pip install -r requirements.txt
./venv/Scripts/python.exe -m patchright install chromium

$env:DATABASE_URL = "postgresql://adspy:adspy@localhost:5432/adspy"
$env:GEMINI_API_KEY = "your-gemini-key"
$env:IMAGES_DIR = "./reports/images"   # local folder instead of the Docker volume
./venv/Scripts/python.exe start_worker.py
```

A visible Chromium window opens by default locally (`HEADLESS` unset/false)
so you can watch the scrape; the Docker image sets `HEADLESS=true` since the
server has no display.
