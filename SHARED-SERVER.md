# Shared server layout (one box, many apps)

This app runs on the **intelligentspeech** Hetzner server alongside other projects,
behind **one** shared Caddy reverse proxy. There is no second proxy in this repo.

```
                 internet
                    │
        ┌───────────┴───────────┐   ports 80/443 (the ONE front door)
        │   Caddy (container     │
        │   name: intelligentspeech)
        └───────────┬───────────┘
   routes by domain name, over the shared "web" docker network:
        │
        ├─ intelligentspeech.duckdns.org → asr:8000        (speech app)
        └─ adspyagent.duckdns.org        → adspy:4000      (this app)
```

## The one server
- **IP:** 167.233.26.80
- **SSH:** `ssh -i C:\Users\Amit\.ssh\intelligentspeech root@167.233.26.80`
- **Apps live in:** `/opt/<project>` — one folder per project
- **Shared network:** `web` (external docker network all apps + Caddy join)

## Update THIS app
```bash
ssh -i C:\Users\Amit\.ssh\intelligentspeech root@167.233.26.80
cd /opt/ad-spy-agent && git pull && docker compose up -d --build
```

## Add a FUTURE project (the easy part)
1. Put it in `/opt/<newproject>` with a `docker-compose.yml` that has NO published
   80/443 ports, NO bundled proxy, and `networks: [web]` (external).
2. Add one block to `/opt/intelligentspeech/Caddyfile`:
   ```
   newproject.duckdns.org {
       reverse_proxy newservice:PORT
   }
   ```
3. `cd /opt/intelligentspeech && docker compose restart caddy`

That's it — copy a folder, add a few lines, reload the proxy.
