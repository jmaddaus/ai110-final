"""Drive the Streamlit app with Playwright and capture screenshots
of a few representative searches.

Usage:
    python -m scripts.screenshot_app

Assumes Streamlit is already running on http://localhost:8501.
Writes PNGs to screenshots/ui_*.png.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

from playwright.sync_api import Page, sync_playwright

BASE_URL = "http://localhost:8501"
OUT = Path(__file__).resolve().parent.parent / "screenshots"

SEEDS = [
    ("ui_tracktags_humble", "HUMBLE", "default"),
    ("ui_tracktags_drivers", "drivers license", "default"),
    ("ui_tracktags_august", "august", "default"),
    ("ui_tracktags_zeppelin", "Black Dog", "default"),
]


def wait_for_streamlit(page: Page, label: str, timeout_ms: int = 30_000) -> None:
    """Wait until Streamlit is idle (no spinner, no running indicator)."""
    page.wait_for_load_state("networkidle", timeout=timeout_ms)
    deadline = time.time() + timeout_ms / 1000
    while time.time() < deadline:
        running = page.locator('[data-testid="stStatusWidget"]').count()
        if running == 0:
            break
        time.sleep(0.3)


def search_and_capture(page: Page, slug: str, query: str, mode: str) -> None:
    print(f"  [{slug}] query={query!r} mode={mode}")
    # Reload to clear any previous search state cleanly
    page.goto(BASE_URL, wait_until="networkidle")
    wait_for_streamlit(page, f"{slug} initial load", timeout_ms=60_000)

    if mode == "discovery":
        # The mode radio button has the label "Discovery (non-obvious)"
        page.get_by_text("Discovery (non-obvious)").click()
        wait_for_streamlit(page, f"{slug} mode toggle", timeout_ms=30_000)

    search_input = page.get_by_placeholder("e.g., Led Zeppelin")
    search_input.click()
    search_input.fill(query)
    search_input.press("Enter")
    page.wait_for_selector('[data-testid="stSelectbox"]', timeout=30_000)
    wait_for_streamlit(page, f"{slug} after search", timeout_ms=60_000)

    time.sleep(8)

    out_path = OUT / f"{slug}.png"
    page.screenshot(path=str(out_path), full_page=True)
    print(f"  [{slug}] saved {out_path}")


def main() -> int:
    OUT.mkdir(exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(viewport={"width": 1400, "height": 1800})
        page = context.new_page()
        for slug, query, mode in SEEDS:
            try:
                search_and_capture(page, slug, query, mode)
            except Exception as e:
                print(f"  [{slug}] FAILED: {e}", file=sys.stderr)
        browser.close()
    print(f"\nDone. Screenshots written to {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
