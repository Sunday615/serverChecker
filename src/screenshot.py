from __future__ import annotations

from pathlib import Path

from playwright.sync_api import sync_playwright


def capture_html_screenshot(
    html_path: Path,
    image_path: Path,
    width: int = 1600,
    height: int = 1200,
) -> Path:
    html_uri = html_path.resolve().as_uri()

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(
            viewport={"width": width, "height": height},
            device_scale_factor=1,
        )
        page.goto(html_uri, wait_until="load")
        page.wait_for_timeout(100)

        terminal = page.locator(".terminal")
        if terminal.count() > 0:
            terminal.screenshot(path=str(image_path))
        else:
            page.screenshot(path=str(image_path), full_page=True)

        browser.close()

    return image_path