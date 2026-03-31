from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.screenshot import capture_html_screenshot
from src.utils import ensure_dir


def main() -> int:
    if len(sys.argv) != 3:
        print("Usage: regenerate_screenshot.py <html_path> <image_path>", file=sys.stderr)
        return 2

    html_path = Path(sys.argv[1]).expanduser()
    image_path = Path(sys.argv[2]).expanduser()

    if not html_path.exists():
        print(f"HTML source not found: {html_path}", file=sys.stderr)
        return 3

    ensure_dir(image_path.parent)
    capture_html_screenshot(html_path=html_path, image_path=image_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
