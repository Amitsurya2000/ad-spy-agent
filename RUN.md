# Running Ad Spy Agent locally + sharing a public URL

The app scrapes the Facebook Ad Library with a real Chromium browser, so it runs
on your own machine (best scraping success rate). An ngrok tunnel exposes it on a
public URL while your PC is on.

## One-click (Windows)

Double-click **`run.bat`**. It opens two windows:

1. **AdSpy Server** — the Flask app on http://localhost:4000
2. **ngrok tunnel** — your public `https://<random>.ngrok-free.dev` URL
   (also visible at http://localhost:4040)

> First-time visitors see an ngrok warning page — they click **"Visit Site"** once.

## Manual steps

```powershell
# Terminal 1 - start the app (key is read from .gemini_key by run.bat;
# set it manually here if running by hand)
cd D:\ad-spy-agent
$env:GEMINI_API_KEY = "your-gemini-key"
.\venv\Scripts\python.exe start.py

# Terminal 2 - expose it publicly
C:\Users\Amit\ngrok\ngrok.exe http 4000
```

## First-time setup (only once)

```powershell
cd D:\ad-spy-agent
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
.\venv\Scripts\python.exe -m patchright install chromium
ngrok config add-authtoken <your-ngrok-token>
```

## Gemini API key

Put your key in a file named **`.gemini_key`** in this folder (one line, the key only).
It is gitignored and never committed. Without it the app still runs, but the
Clone / AI Rewrite / Niche-Transform features are disabled.

## Notes

- **Data persistence:** research jobs are saved to `reports/_history.json` and
  reload on startup. Use the **History** button in the dashboard to revisit them.
- **The public ngrok URL changes** every restart on the free plan. A fixed domain
  requires a paid ngrok plan.
- The app is reachable only while the PC is awake and both windows are running.
