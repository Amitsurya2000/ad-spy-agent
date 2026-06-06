"""
Viral Ad Cloner - Web Server
Flask API + Dashboard on localhost:4000
"""

import asyncio
import json
import os
import re
import threading
from flask import Flask, jsonify, request, send_from_directory

from .agent import AdSpyAgent
from .report import save_json, save_csv

app = Flask(__name__, static_folder="static")

research_store = {}
active_jobs = {}

REPORTS_DIR = os.path.join(os.path.dirname(__file__), "..", "reports")
IMAGES_DIR = os.path.join(REPORTS_DIR, "images")
os.makedirs(REPORTS_DIR, exist_ok=True)
os.makedirs(IMAGES_DIR, exist_ok=True)

# Persistent history: research jobs survive server restarts (stored on disk).
STORE_FILE = os.path.join(REPORTS_DIR, "_history.json")


def load_history():
    """Reload completed/failed jobs from disk into the in-memory store."""
    try:
        with open(STORE_FILE, "r", encoding="utf-8") as f:
            saved = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return
    research_store.update(saved)
    for jid, entry in saved.items():
        active_jobs[jid] = entry.get("status", "completed")
    if saved:
        print(f"  Loaded {len(saved)} saved job(s) from history")


def save_history():
    """Persist the current research store to disk."""
    try:
        with open(STORE_FILE, "w", encoding="utf-8") as f:
            json.dump(research_store, f)
    except OSError as e:
        print(f"  Could not save history: {e}")


HAS_GEMINI = bool(os.environ.get("GEMINI_API_KEY", ""))

# On a server (no display) the browser MUST run headless. Locally it defaults
# to a visible window so you can watch the automation. Override with HEADLESS=true.
HEADLESS = os.environ.get("HEADLESS", "false").lower() in ("1", "true", "yes")

load_history()


@app.route("/api/research", methods=["POST"])
def start_research():
    data = request.get_json()
    query = data.get("query", "").strip()
    if not query:
        return jsonify({"error": "Query is required"}), 400

    country = data.get("country", "ALL")
    max_ads = min(int(data.get("max_ads", 30)), 50)
    scroll_rounds = min(int(data.get("scroll_rounds", 5)), 10)

    job_id = re.sub(r'[^a-zA-Z0-9]', '_', query.lower()) + f"_{id(query) % 10000}"

    if job_id in active_jobs and active_jobs[job_id] == "running":
        return jsonify({"error": "Research already in progress", "job_id": job_id}), 409

    active_jobs[job_id] = "running"

    def run_agent():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            agent = AdSpyAgent(
                headless=HEADLESS,
                max_ads=max_ads,
                scroll_rounds=scroll_rounds,
                images_dir=IMAGES_DIR,
            )
            ads = loop.run_until_complete(
                agent.research(query, country, use_gemini=HAS_GEMINI)
            )

            safe_name = re.sub(r'[^a-zA-Z0-9_-]', '_', query.lower())
            json_path = os.path.join(REPORTS_DIR, f"{safe_name}_ads.json")
            csv_path = os.path.join(REPORTS_DIR, f"{safe_name}_ads.csv")
            save_json(agent.ads, agent.brand_info, json_path)
            save_csv(agent.ads, csv_path)

            research_store[job_id] = {
                "status": "completed",
                "query": query,
                "brand_info": agent.brand_info,
                "ads": agent.ads,
                "copy_dna": agent.copy_dna,
                "creative_dna": agent.creative_dna,
                "gemini_copy_dna": agent.gemini_copy_dna,
                "gemini_creative_dna": agent.gemini_creative_dna,
                "image_analyses": agent.image_analyses,
                "has_gemini": HAS_GEMINI,
                "json_file": f"{safe_name}_ads.json",
                "csv_file": f"{safe_name}_ads.csv",
            }
            active_jobs[job_id] = "completed"
            save_history()
        except Exception as e:
            import traceback
            traceback.print_exc()
            research_store[job_id] = {"status": "failed", "query": query, "error": str(e)}
            active_jobs[job_id] = "failed"
            save_history()
        finally:
            loop.close()

    thread = threading.Thread(target=run_agent, daemon=True)
    thread.start()
    return jsonify({"job_id": job_id, "status": "running", "query": query})


@app.route("/api/research/<job_id>", methods=["GET"])
def get_research(job_id):
    if job_id in research_store:
        return jsonify(research_store[job_id])
    if job_id in active_jobs:
        return jsonify({"status": active_jobs[job_id], "job_id": job_id})
    return jsonify({"error": "Job not found"}), 404


@app.route("/api/research", methods=["GET"])
def list_research():
    jobs = []
    for jid, status in active_jobs.items():
        entry = {"job_id": jid, "status": status}
        if jid in research_store:
            entry["query"] = research_store[jid].get("query", "")
            entry["ad_count"] = len(research_store[jid].get("ads", []))
        jobs.append(entry)
    return jsonify(jobs)


@app.route("/api/rewrite", methods=["POST"])
def generate_rewrite():
    """Generate AI-powered ad rewrites using Gemini."""
    data = request.get_json()
    job_id = data.get("job_id", "")
    product_name = data.get("product_name", "")
    product_desc = data.get("product_desc", "")
    target_audience = data.get("target_audience", "")

    if job_id not in research_store or research_store[job_id].get("status") != "completed":
        return jsonify({"error": "Research not found or not completed"}), 404

    stored = research_store[job_id]

    # Try Gemini-powered rewrite first
    if HAS_GEMINI:
        try:
            from .gemini_engine import GeminiEngine
            gemini = GeminiEngine()
            copy_dna = stored.get("gemini_copy_dna") or stored.get("copy_dna", {})
            creative_dna = stored.get("gemini_creative_dna") or stored.get("creative_dna", {})
            rewrites = gemini.rewrite_ad(
                copy_dna, creative_dna,
                product_name, product_desc, target_audience,
                num_versions=6,
            )
            return jsonify({
                "rewrites": rewrites,
                "copy_dna": copy_dna,
                "creative_dna": creative_dna,
                "engine": "gemini",
            })
        except Exception as e:
            print(f"Gemini rewrite failed: {e}, falling back to rule-based")

    # Fallback to rule-based
    agent = AdSpyAgent()
    agent.ads = stored.get("ads", [])
    agent.brand_info = stored.get("brand_info", {})
    agent.copy_dna = stored.get("copy_dna", {})
    rewrites = agent.generate_rewrites(product_name, product_desc, target_audience)
    return jsonify({"rewrites": rewrites, "copy_dna": agent.copy_dna, "engine": "rule-based"})


@app.route("/api/clone", methods=["POST"])
def clone_ad():
    """Clone a specific ad using Gemini."""
    if not HAS_GEMINI:
        return jsonify({"error": "Gemini API key not set. Export GEMINI_API_KEY."}), 400

    data = request.get_json()
    job_id = data.get("job_id", "")
    ad_index = int(data.get("ad_index", 0))
    product_name = data.get("product_name", "")
    product_desc = data.get("product_desc", "")

    if job_id not in research_store:
        return jsonify({"error": "Research not found"}), 404

    stored = research_store[job_id]
    ads = stored.get("ads", [])
    if ad_index >= len(ads):
        return jsonify({"error": "Ad index out of range"}), 400

    original_ad = ads[ad_index]
    # Use full_breakdown visual data if available, else empty
    image_analysis = original_ad.get("full_breakdown", {}).get("visual_breakdown", {})

    try:
        from .gemini_engine import GeminiEngine
        gemini = GeminiEngine()
        clone = gemini.clone_specific_ad(original_ad, image_analysis, product_name, product_desc)
        return jsonify({"clone": clone, "original": original_ad})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/niche-transform", methods=["POST"])
def niche_transform():
    """Transform winning DNA into a different niche."""
    if not HAS_GEMINI:
        return jsonify({"error": "Gemini API key required."}), 400

    data = request.get_json()
    job_id = data.get("job_id", "")
    target_niche = data.get("target_niche", "")
    product_name = data.get("product_name", "")
    product_desc = data.get("product_desc", "")

    if job_id not in research_store:
        return jsonify({"error": "Research not found"}), 404

    stored = research_store[job_id]
    copy_dna = stored.get("gemini_copy_dna") or stored.get("copy_dna", {})
    original_niche = stored.get("query", "unknown")

    try:
        from .gemini_engine import GeminiEngine
        gemini = GeminiEngine()
        results = gemini.niche_transform(copy_dna, original_niche, target_niche, product_name, product_desc)
        return jsonify({"transforms": results, "original_niche": original_niche, "target_niche": target_niche})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/download/<filename>")
def download_file(filename):
    return send_from_directory(REPORTS_DIR, filename, as_attachment=True)


@app.route("/api/images/<filename>")
def serve_image(filename):
    return send_from_directory(IMAGES_DIR, filename)


@app.route("/api/status")
def api_status():
    return jsonify({"gemini_enabled": HAS_GEMINI})


@app.route("/")
def dashboard():
    return send_from_directory(app.static_folder, "index.html")


@app.route("/<path:path>")
def static_files(path):
    return send_from_directory(app.static_folder, path)


def run_server(port=4000):
    print(f"\n  Viral Ad Cloner running at: http://localhost:{port}")
    print(f"  Gemini AI: {'ENABLED' if HAS_GEMINI else 'DISABLED (set GEMINI_API_KEY)'}\n")
    app.run(host="0.0.0.0", port=port, debug=False)


if __name__ == "__main__":
    run_server()
