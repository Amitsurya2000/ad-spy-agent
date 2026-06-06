# Deploying Ad Spy Agent (Oracle Cloud + Dokploy + Docker)

This deploys the app to a 24/7 server using the GitHub → Dokploy → Docker pipeline.

```
You + Claude Code → GitHub push → Dokploy (auto build & deploy) → Oracle server → live URL
```

> ⚠️ **Scraping caveat:** the app drives a real Chromium browser against the
> Facebook Ad Library. From a cloud/datacenter IP, Facebook may block or
> CAPTCHA the scraper. The dashboard + Gemini AI features run fine on the
> server; if scraping gets blocked, run scrapes from a home IP or add a
> residential proxy. The app runs the browser **headless** on the server
> (set automatically via `HEADLESS=true`).

---

## 1. Create the Oracle server

1. OCI Console → **Compute → Instances → Create instance**
2. **Image:** Canonical Ubuntu 22.04
3. **Shape:** Ampere → `VM.Standard.A1.Flex` → **4 OCPU / 24 GB** (Always Free).
   If "out of capacity", retry another Availability Domain or later.
4. **Assign public IPv4 = Yes**
5. **SSH keys:** paste your public key (`retirement360.pub` or any key you made
   with `ssh-keygen -t ed25519`).
6. **Boot volume:** 50–100 GB.
7. Create → wait for **RUNNING** → copy the **Public IP**.

## 2. Open ports (TWO layers — both required)

**A. Oracle Security List** (VCN → Security Lists → default → Add Ingress, source `0.0.0.0/0`, TCP):
`80`, `443`, `3000` (Dokploy UI — ideally restrict to your IP).

**B. The OS firewall** (Oracle Ubuntu blocks everything but SSH). After SSH in:
```bash
sudo iptables -I INPUT 6 -p tcp --dport 80 -j ACCEPT
sudo iptables -I INPUT 6 -p tcp --dport 443 -j ACCEPT
sudo iptables -I INPUT 6 -p tcp --dport 3000 -j ACCEPT
sudo netfilter-persistent save
```

## 3. SSH in + install Dokploy (installs Docker too)
```bash
ssh -i <path-to-private-key> ubuntu@<PUBLIC_IP>
sudo apt update && sudo apt upgrade -y
curl -sSL https://dokploy.com/install.sh | sh
```
Open `http://<PUBLIC_IP>:3000` → create the Dokploy admin account.

## 4. Deploy the app in Dokploy

1. **Connect GitHub:** Dokploy → Settings → Git → connect your GitHub account
   (or add a Personal Access Token). Authorize the `ad-spy-agent` repo.
2. **Create Project → Create Application** → source = your `ad-spy-agent` repo,
   branch `main`. Build type = **Dockerfile** (Dokploy auto-detects the Dockerfile).
3. **Environment variables** (Application → Environment):
   ```
   GEMINI_API_KEY = <your AIza... key>
   HEADLESS = true
   ```
   (Never commit the key — set it here only.)
4. **Port:** the app listens on **4000** (Dokploy maps it via Traefik).
5. **Persistent volume** (so history/images survive redeploys):
   mount a volume at container path `/app/reports`.
6. **Domain (optional):** add your domain under the app's Domains tab; Dokploy
   provisions free HTTPS (Let's Encrypt) via Traefik automatically. Point your
   domain's **A record → the Oracle Public IP** first.
7. Click **Deploy**. Dokploy pulls the repo, builds the Docker image, and runs it.

## 5. Auto-deploy on every push
Enable **Auto Deploy** (webhook) in the app settings. Then:
```
git push  →  Dokploy rebuilds & redeploys automatically
```

---

## Updating the app later
```bash
git add -A && git commit -m "..." && git push
```
Dokploy redeploys on its own (if auto-deploy is on) — or click **Deploy** in the UI.

## Notes
- First build is slow (~5–10 min): it installs Chromium + OS libs. Later builds are cached.
- Logs: Dokploy → Application → Logs (or `docker logs <container>` over SSH).
- The Gemini key lives only in Dokploy env vars, never in the image (`.dockerignore` excludes `.gemini_key`).
