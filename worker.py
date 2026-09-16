"""
Worker - polls Postgres for pending research jobs, runs the Facebook Ad
Library scrape via AdSpyAgent (unchanged), and writes the results (ads, DNA)
straight into Postgres. Ad screenshots are written directly onto the shared
`ad_images` volume (see docker-compose.yml) - Caddy serves that directory as
static files, so there's no separate "upload" step.

The worker has no HTTP server of its own: it needs no inbound port, tunnel,
or reverse proxy - just a connection to Postgres, plus outbound access to
Facebook and Gemini.

Run via `python start_worker.py` (see DEPLOY.md), not directly - this module
uses relative imports and depends on the package-registration trick in
start_worker.py, same as the old start.py did for the original Flask server.
"""

import asyncio
import os
import time
import traceback

import psycopg
from psycopg.types.json import Json

from .agent import AdSpyAgent

POLL_INTERVAL_SECONDS = int(os.environ.get("WORKER_POLL_INTERVAL", "5"))
HEADLESS = os.environ.get("HEADLESS", "false").lower() in ("1", "true", "yes")
HAS_GEMINI = bool(os.environ.get("GEMINI_API_KEY", ""))

# Root of the shared volume Caddy also mounts (read-only) at /srv/ad-images
# and serves under /images/*. Each job's screenshots land in a subfolder
# named after the job id, matching the image_url stored in Postgres.
IMAGES_ROOT = os.environ.get("IMAGES_DIR", "/data/ad-images")


def get_connection() -> psycopg.Connection:
    database_url = os.environ.get("DATABASE_URL", "")
    if not database_url:
        raise RuntimeError("DATABASE_URL must be set (see .env.example).")
    return psycopg.connect(database_url, autocommit=True)


def claim_next_job(conn: psycopg.Connection):
    """Atomically claim the oldest pending job, or None if there isn't one.

    FOR UPDATE SKIP LOCKED is the standard Postgres job-queue pattern: it
    locks (and skips, for any other worker) exactly one pending row, so two
    workers can never claim the same job.
    """
    with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
        cur.execute(
            """
            update research_jobs
            set status = 'running'
            where id = (
                select id from research_jobs
                where status = 'pending'
                order by created_at
                for update skip locked
                limit 1
            )
            returning id, query, country, max_ads, scroll_rounds, use_gemini
            """
        )
        return cur.fetchone()


def save_results(conn: psycopg.Connection, job_id: str, agent: AdSpyAgent) -> None:
    with conn.cursor() as cur:
        # Re-running a job (rare, but possible) shouldn't duplicate rows.
        cur.execute("delete from ads where job_id = %s", (job_id,))

        for ad in agent.ads:
            cb = ad.get("copy_breakdown", {})
            cur.execute(
                """
                insert into ads (
                    job_id, ad_id, platform, status, start_date,
                    primary_text, headline, cta, media_type,
                    angle, funnel_stage, copy_breakdown, full_breakdown,
                    image_path, image_url
                ) values (
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s
                )
                """,
                (
                    job_id,
                    ad.get("ad_id", ""),
                    ad.get("platform", ""),
                    ad.get("status", ""),
                    ad.get("start_date", ""),
                    ad.get("primary_text", ""),
                    ad.get("headline", ""),
                    ad.get("cta", ""),
                    ad.get("media_type", ""),
                    ad.get("angle", ""),
                    ad.get("funnel_stage", ""),
                    Json(cb),
                    Json(ad.get("full_breakdown", {})),
                    ad.get("image_path", ""),
                    ad.get("image_url", ""),
                ),
            )

        cur.execute(
            """
            update research_jobs
            set status = 'completed',
                brand_info = %s,
                copy_dna = %s,
                creative_dna = %s,
                gemini_copy_dna = %s,
                gemini_creative_dna = %s
            where id = %s
            """,
            (
                Json(agent.brand_info),
                Json(agent.copy_dna),
                Json(agent.creative_dna),
                Json(agent.gemini_copy_dna),
                Json(agent.gemini_creative_dna),
                job_id,
            ),
        )


def stamp_image_urls(job_id: str, images_dir: str, ads: list) -> None:
    """Point each ad at the path Caddy will serve it from. The file is
    already on disk (agent.py wrote it into images_dir) - nothing to upload."""
    for ad in ads:
        img_file = ad.get("image_file", "")
        if not img_file:
            continue
        local_path = os.path.join(images_dir, img_file)
        if not os.path.exists(local_path):
            continue
        ad["image_path"] = f"{job_id}/{img_file}"
        ad["image_url"] = f"/images/{job_id}/{img_file}"


def run_job(conn: psycopg.Connection, job: dict) -> None:
    job_id = job["id"]
    print(f"\n[worker] Starting job {job_id}: '{job['query']}'")

    images_dir = os.path.join(IMAGES_ROOT, str(job_id))
    os.makedirs(images_dir, exist_ok=True)

    agent = AdSpyAgent(
        headless=HEADLESS,
        max_ads=job.get("max_ads") or 30,
        scroll_rounds=job.get("scroll_rounds") or 5,
        images_dir=images_dir,
    )

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(
            agent.research(job["query"], job.get("country") or "ALL", use_gemini=HAS_GEMINI)
        )
        stamp_image_urls(str(job_id), images_dir, agent.ads)
        save_results(conn, job_id, agent)
        print(f"[worker] Job {job_id} completed ({len(agent.ads)} ads).")
    except Exception as e:
        traceback.print_exc()
        with conn.cursor() as cur:
            cur.execute(
                "update research_jobs set status = 'failed', error = %s where id = %s",
                (str(e), job_id),
            )
        print(f"[worker] Job {job_id} failed: {e}")
    finally:
        loop.close()


def main_loop():
    print("=" * 64)
    print("  AD SPY AGENT - WORKER")
    print(f"  Polling Postgres every {POLL_INTERVAL_SECONDS}s "
          f"(headless={HEADLESS}, gemini={HAS_GEMINI})")
    print("=" * 64)

    conn = get_connection()
    while True:
        try:
            job = claim_next_job(conn)
            if job:
                run_job(conn, job)
            else:
                time.sleep(POLL_INTERVAL_SECONDS)
        except KeyboardInterrupt:
            print("\n[worker] Stopped.")
            break
        except psycopg.OperationalError:
            traceback.print_exc()
            print("[worker] Lost connection to Postgres, reconnecting...")
            time.sleep(POLL_INTERVAL_SECONDS)
            try:
                conn.close()
            except Exception:
                pass
            conn = get_connection()
        except Exception:
            traceback.print_exc()
            time.sleep(POLL_INTERVAL_SECONDS)
