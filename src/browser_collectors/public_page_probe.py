import argparse
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from playwright.sync_api import sync_playwright


def probe_pages(pages):
    results = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1365, "height": 900})
        for target in pages:
            row = {
                "id": target["id"],
                "label": target["label"],
                "url": target["url"],
                "status": "failed",
                "title": "",
                "final_url": "",
                "note": "",
            }
            try:
                page.goto(target["url"], wait_until="domcontentloaded", timeout=30000)
                row["title"] = page.title()
                row["final_url"] = page.url
                if "error" in row["title"].lower():
                    row["status"] = "needs_review"
                    row["note"] = "페이지는 열렸지만 오류 화면으로 보입니다. 세부 조회 자동화 전 URL/접근 조건 점검이 필요합니다."
                else:
                    row["status"] = "reachable"
                    row["note"] = "공개 페이지 접근 가능. 세부 표/검색 조건은 DOM 기반 자동화로 확장합니다."
            except Exception as exc:
                row["note"] = f"{type(exc).__name__}: {exc}"
            results.append(row)
        browser.close()
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    config = json.loads(Path(args.config).read_text(encoding="utf-8"))
    now = datetime.now(ZoneInfo("Asia/Seoul")).strftime("%Y-%m-%d %H:%M:%S")
    payload = {
        "collected_at": now,
        "timezone": "Asia/Seoul",
        "provider": "Playwright browser public page probe",
        "pages": probe_pages(config["pages"]),
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {output_path}")


if __name__ == "__main__":
    main()
