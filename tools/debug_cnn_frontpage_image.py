import re
from pathlib import Path
from html import unescape

RAW_PATH = Path("tools/cnn_homepage_raw.html")
TITLE = "US releases official agreement with Iran"
URL = "https://www.cnn.com/2026/06/17/middleeast/us-iran-war-mou-text-intl"


def clean(value):
    value = unescape(str(value or ""))
    value = value.replace("\\/", "/")
    value = value.replace("&amp;", "&")
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def extract_images(block):
    patterns = [
        r'https?:\\?/\\?/media\.cnn\.com/api/v1/images/stellar/prod/[^"\'<>\s,]+',
        r'https?:\\?/\\?/media\.cnn\.com/[^"\'<>\s,]+\.(?:jpg|jpeg|png|webp)(?:\?[^"\'<>\s,]+)?',
        r'https?:\\?/\\?/cdn\.cnn\.com/[^"\'<>\s,]+\.(?:jpg|jpeg|png|webp)(?:\?[^"\'<>\s,]+)?',
        r'"uri"\s*:\s*"([^"]+)"',
        r'"url"\s*:\s*"([^"]+\.(?:jpg|jpeg|png|webp)[^"]*)"',
    ]

    found = []

    for pattern in patterns:
        for match in re.finditer(pattern, block, flags=re.I):
            raw = match.group(1) if match.groups() else match.group(0)
            image = clean(raw)

            if image.startswith("//"):
                image = "https:" + image

            if image.startswith("/"):
                image = "https://www.cnn.com" + image

            low = image.lower()

            if not any(host in low for host in ["media.cnn.com", "cdn.cnn.com", "cnn.com"]):
                continue

            if any(bad in low for bad in ["logo", "favicon", "sprite", "icon", "placeholder", "avatar"]):
                continue

            if image not in found:
                found.append(image)

    return found


def show_context(label, html, index, before, after):
    start = max(0, index - before)
    end = min(len(html), index + after)
    block = html[start:end]

    images = extract_images(block)

    print("")
    print("=" * 100)
    print(label)
    print(f"html range: {start:,} - {end:,}")
    print(f"images found: {len(images)}")
    print("=" * 100)

    for i, image in enumerate(images, 1):
        print(f"{i:02d}. {image}")

    return images


def main():
    html = RAW_PATH.read_text(encoding="utf-8", errors="replace")

    title_idx = html.find(TITLE)
    url_idx = html.find(URL.replace("https://www.cnn.com", ""))

    print(f'TITLE INDEX: {title_idx}')
    print(f'URL INDEX: {url_idx}')

    all_images = []

    if title_idx >= 0:
        all_images.extend(show_context("IMAGES AROUND EXACT HEADLINE TEXT", html, title_idx, 12000, 12000))
        all_images.extend(show_context("TIGHT IMAGES AROUND EXACT HEADLINE TEXT", html, title_idx, 4500, 4500))

    if url_idx >= 0:
        all_images.extend(show_context("IMAGES AROUND ARTICLE URL", html, url_idx, 12000, 12000))
        all_images.extend(show_context("TIGHT IMAGES AROUND ARTICLE URL", html, url_idx, 4500, 4500))

    deduped = []
    for image in all_images:
        if image not in deduped:
            deduped.append(image)

    print("")
    print("=" * 100)
    print(f'1. CNN: "{TITLE}"')
    print(f"URL: {URL}")
    print("FRONTPAGE IMAGE CANDIDATES, DEDUPED:")
    for i, image in enumerate(deduped, 1):
        print(f"{i:02d}. {image}")
    print("=" * 100)


if __name__ == "__main__":
    main()
