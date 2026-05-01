import argparse
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run(args):
    subprocess.run([sys.executable, *args], cwd=ROOT, check=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--publish-dir", default="public")
    parser.add_argument("--open", action="store_true")
    args = parser.parse_args()

    run(["src/collect_stooq_snapshot.py", "--output", "data/market_snapshot.json"])
    run(["src/collect_naver_market.py", "--output", "data/kr_market_snapshot.json"])
    run(["src/collect_google_news_rss.py", "--config", "config/news_queries.json", "--output", "data/news_snapshot.json"])
    run(["src/analyze_news.py", "--news", "data/news_snapshot.json", "--output", "data/news_analysis.json", "--recent-hours", "36"])
    run(["src/browser_collectors/public_page_probe.py", "--config", "config/public_pages.json", "--output", "data/public_page_probe.json"])
    run(["src/browser_collectors/collect_rone_dashboard.py", "--output", "data/rone_dashboard.json"])
    run(["src/browser_collectors/collect_molit_public_info.py", "--output", "data/molit_public_info.json"])
    run([
        "src/build_actual_payload.py",
        "--base", "data/sample_daily_payload.json",
        "--snapshot", "data/market_snapshot.json",
        "--news-analysis", "data/news_analysis.json",
        "--kr-market", "data/kr_market_snapshot.json",
        "--page-probe", "data/public_page_probe.json",
        "--rone", "data/rone_dashboard.json",
        "--molit-info", "data/molit_public_info.json",
        "--output", "data/actual_daily_payload.json",
    ])
    run(["src/generate_report.py", "--input", "data/actual_daily_payload.json", "--output", "output/actual_daily_report.html"])

    publish_dir = ROOT / args.publish_dir
    publish_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / "output/actual_daily_report.html", publish_dir / "index.html")
    (publish_dir / ".nojekyll").touch()

    if args.open:
        import os
        os.startfile(publish_dir / "index.html")

    print(f"published {publish_dir / 'index.html'}")


if __name__ == "__main__":
    main()
