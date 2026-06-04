"""
Report generator - produces JSON, CSV, and a terminal summary.
"""

import csv
import json
import os
from collections import Counter


def save_json(ads: list, brand_info: dict, path: str):
    """Save full research data to JSON."""
    payload = {"brand": brand_info, "ads": ads}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)


def save_csv(ads: list, path: str):
    """Save ad data to CSV for spreadsheet analysis."""
    if not ads:
        return

    fields = [
        "ad_id", "platform", "status", "start_date",
        "primary_text", "headline", "cta", "media_type",
        "angle", "funnel_stage",
        "hook", "problem", "solution", "offer", "copy_cta",
    ]

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for ad in ads:
            cb = ad.get("copy_breakdown", {})
            row = {
                "ad_id": ad.get("ad_id", ""),
                "platform": ad.get("platform", ""),
                "status": ad.get("status", ""),
                "start_date": ad.get("start_date", ""),
                "primary_text": ad.get("primary_text", ""),
                "headline": ad.get("headline", ""),
                "cta": ad.get("cta", ""),
                "media_type": ad.get("media_type", ""),
                "angle": ad.get("angle", ""),
                "funnel_stage": ad.get("funnel_stage", ""),
                "hook": cb.get("hook", ""),
                "problem": cb.get("problem", ""),
                "solution": cb.get("solution", ""),
                "offer": cb.get("offer", ""),
                "copy_cta": cb.get("cta", ""),
            }
            writer.writerow(row)


def print_summary(ads: list, brand_info: dict):
    """Print a rich terminal summary of the research."""
    query = brand_info.get("query", "?")
    brand = brand_info.get("matched_brand", "?")
    total = brand_info.get("total_results", "?")
    sep = "=" * 64

    print(f"\n{sep}")
    print(f"  AD SPY AGENT - RESEARCH REPORT")
    print(f"{sep}")
    print(f"  Search Query   : {query}")
    print(f"  Matched Brand  : {brand}")
    print(f"  Total in Library: {total}")
    print(f"  Ads Scraped    : {len(ads)}")
    print(sep)

    if not ads:
        print("  No ads found.")
        return

    # --- Status breakdown ---
    statuses = Counter(a.get("status", "Unknown") for a in ads)
    print("\n  STATUS BREAKDOWN")
    print("  " + "-" * 30)
    for s, c in statuses.most_common():
        bar = "#" * c
        print(f"    {s:<12} {c:>3}  {bar}")

    # --- CTA breakdown ---
    ctas = Counter(a.get("cta", "N/A") for a in ads)
    print("\n  CTA BREAKDOWN")
    print("  " + "-" * 30)
    for ct, c in ctas.most_common():
        bar = "#" * c
        print(f"    {ct:<16} {c:>3}  {bar}")

    # --- Angle breakdown ---
    angles = Counter(a.get("angle", "Unknown") for a in ads)
    print("\n  ANGLE DETECTION")
    print("  " + "-" * 30)
    for ang, c in angles.most_common():
        bar = "#" * c
        print(f"    {ang:<20} {c:>3}  {bar}")

    # --- Funnel breakdown ---
    funnels = Counter(a.get("funnel_stage", "Unknown") for a in ads)
    print("\n  FUNNEL MAPPING")
    print("  " + "-" * 30)
    for f, c in funnels.most_common():
        bar = "#" * c
        print(f"    {f:<16} {c:>3}  {bar}")

    # --- Media types ---
    media = Counter(a.get("media_type", "Unknown") for a in ads)
    print("\n  MEDIA TYPES")
    print("  " + "-" * 30)
    for m, c in media.most_common():
        bar = "#" * c
        print(f"    {m:<30} {c:>3}  {bar}")

    # --- Top 5 ads detail ---
    print(f"\n{sep}")
    print(f"  TOP {min(5, len(ads))} ADS (DETAIL)")
    print(sep)

    for i, ad in enumerate(ads[:5], 1):
        cb = ad.get("copy_breakdown", {})
        print(f"\n  --- Ad #{i} ---")
        print(f"  Ad ID      : {ad.get('ad_id', 'N/A')}")
        print(f"  Platform   : {ad.get('platform', 'N/A')}")
        print(f"  Status     : {ad.get('status', 'N/A')}")
        print(f"  Date       : {ad.get('start_date', 'N/A')}")
        print(f"  Media      : {ad.get('media_type', 'N/A')}")
        print(f"  CTA        : {ad.get('cta', 'N/A')}")
        print(f"  Angle      : {ad.get('angle', 'N/A')}")
        print(f"  Funnel     : {ad.get('funnel_stage', 'N/A')}")
        print(f"  Headline   : {ad.get('headline', 'N/A')[:80]}")
        text = ad.get("primary_text", "")
        if text:
            print(f"  Copy       : {text[:120]}{'...' if len(text) > 120 else ''}")
        print(f"  --- Copy Breakdown ---")
        print(f"    Hook     : {cb.get('hook', 'N/A')[:80]}")
        print(f"    Problem  : {cb.get('problem', 'N/A')[:80]}")
        print(f"    Solution : {cb.get('solution', 'N/A')[:80]}")
        print(f"    Offer    : {cb.get('offer', 'N/A')[:80]}")
        print(f"    CTA      : {cb.get('cta', 'N/A')[:80]}")

    print(f"\n{sep}\n")
