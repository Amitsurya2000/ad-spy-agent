"""
CLI entry point for the AdSpy Agent.

Usage:
    python -m ad_spy_agent "Nike"
    python -m ad_spy_agent "Coaching" --country US --max-ads 50
    python -m ad_spy_agent "Real Estate Mumbai" --headless --output reports/
"""

import argparse
import asyncio
import os
import re
import sys

from .agent import AdSpyAgent
from .report import save_json, save_csv, print_summary


def parse_args():
    parser = argparse.ArgumentParser(
        prog="ad_spy_agent",
        description="AdSpy Agent - Facebook Ad Library Research Automation",
    )
    parser.add_argument(
        "query",
        help="Brand name or keyword to search (e.g. 'Nike', 'Coaching')",
    )
    parser.add_argument(
        "--country",
        default="ALL",
        help="Country code filter (default: ALL). Examples: US, IN, GB",
    )
    parser.add_argument(
        "--max-ads",
        type=int,
        default=30,
        help="Maximum number of ads to scrape (default: 30)",
    )
    parser.add_argument(
        "--scroll-rounds",
        type=int,
        default=5,
        help="Number of scroll rounds to load more ads (default: 5)",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run browser in headless mode (no visible window)",
    )
    parser.add_argument(
        "--output",
        default=".",
        help="Output directory for reports (default: current directory)",
    )
    return parser.parse_args()


async def run(args):
    agent = AdSpyAgent(
        headless=args.headless,
        max_ads=args.max_ads,
        scroll_rounds=args.scroll_rounds,
    )

    print("\n" + "=" * 64)
    print("  AD SPY AGENT")
    print("  Facebook Ad Library Research Automation")
    print("=" * 64)

    ads = await agent.research(args.query, args.country)

    if not ads:
        print("No ads found. Try a different query or check your connection.")
        return

    # Create output directory
    os.makedirs(args.output, exist_ok=True)
    safe_name = re.sub(r'[^a-zA-Z0-9_-]', '_', args.query.lower())

    # Save reports
    json_path = os.path.join(args.output, f"{safe_name}_ads.json")
    csv_path = os.path.join(args.output, f"{safe_name}_ads.csv")

    save_json(agent.ads, agent.brand_info, json_path)
    save_csv(agent.ads, csv_path)

    print(f"  Saved: {json_path}")
    print(f"  Saved: {csv_path}")

    # Print terminal summary
    print_summary(agent.ads, agent.brand_info)


def main():
    args = parse_args()
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
