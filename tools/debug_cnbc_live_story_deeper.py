import json
import re
import ssl
import urllib.request
from html import unescape
from pathlib import Path

LIVE_URL = "https://www.cnbc.com/2026/06/17/fed-meeting-today-live-updates.html"
OUT = Path("tools/cnbc_live_story_raw.html")

# Locator only. This is NOT used to select the final headline.
EXPECTED_LOCATOR = "Fed holds rates steady, pares down statement to remove cutting bias"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


def fetch(url):
    req = urllib.request.Request(url, headers=HEADERS)
    ctx = ssl._create_unverified_context()
    with urllib.request.urlopen(req, timeout=20, context=ctx) as resp:
        return resp.read().decode("utf-8", errors="replace")


def clean(value):
    value = unescape(str(value or ""))
    try:
        value = value.encode("utf-8").decode("unicode_escape", errors="ignore")
    except Exception:
        pass
    value = re.sub(r"<[^>]+>", " ", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def extract_balanced_object(source, start_index):
    open_index = source.find("{", start_index)
    if open_index < 0:
        return None

    depth = 0
    in_string = False
    escape = False

    for index in range(open_index, len(source)):
        char = source[index]

        if in_string:
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return source[open_index:index + 1]

    return None


def walk(obj):
    if isinstance(obj, dict):
        yield obj
        for value in obj.values():
            yield from walk(value)
    elif isinstance(obj, list):
        for item in obj:
            yield from walk(item)


def best_title(node):
    for key in [
        "headline",
        "title",
        "shorterHeadline",
        "linkHeadline",
        "promoTitle",
        "name",
        "text",
    ]:
        value = clean(node.get(key, ""))
        if len(value) >= 20:
            return value
    return ""


def node_type_text(node):
    return " ".join(
        clean(node.get(k, ""))
        for k in ["__typename", "type", "contentType", "subType", "moduleName"]
    ).lower()


def is_bad_live_candidate(title, node):
    title_l = title.lower()
    type_l = node_type_text(node)

    if not title or len(title) < 20:
        return True

    bad_bits = [
        "cnbc",
        "subscribe",
        "newsletter",
        "watch:",
        "squawk",
        "what the fed decision means for your money",
        "what to watch ahead",
        "fed meeting live updates",
        "top news and analysis",
        "stock market today",
        "legacyplayercontainer",
        "adbox",
    ]

    if any(bit in title_l for bit in bad_bits):
        return True

    # Prefer live update / live blog objects when present.
    if any(good in type_l for good in ["live", "update", "blog"]):
        return False

    # Still allow normal story-card titles after live objects are exhausted.
    return False


def extract_json_objects_from_live_page(html):
    objects = []

    # CNBC page data block.
    for marker in ["window.__s_data=", "__NEXT_DATA__"]:
        marker_index = html.find(marker)
        if marker_index >= 0:
            raw = extract_balanced_object(html, marker_index + len(marker))
            if raw:
                try:
                    objects.append(json.loads(raw))
                except Exception:
                    pass

    # JSON-LD blocks.
    for match in re.finditer(
        r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        html,
        flags=re.S | re.I,
    ):
        raw = match.group(1).strip()
        try:
            objects.append(json.loads(raw))
        except Exception:
            pass

    return objects


def print_locator_hits(html):
    print("")
    print("LOCATOR CHECK ONLY — not used for final selection")
    print("=" * 100)

    idx = html.lower().find(EXPECTED_LOCATOR.lower())
    if idx < 0:
        print(f'NOT FOUND in raw live page HTML: "{EXPECTED_LOCATOR}"')
    else:
        start = max(0, idx - 1200)
        end = min(len(html), idx + 1800)
        print(f'FOUND in raw live page HTML: "{EXPECTED_LOCATOR}"')
        print(clean(html[start:end])[:2500])


def print_api_like_urls(html):
    print("")
    print("API-LIKE URLS FOUND ON LIVE PAGE")
    print("=" * 100)

    urls = []
    for match in re.finditer(r'https?://[^"\'<> ]+', html):
        url = match.group(0).replace("\\/", "/")
        low = url.lower()
        if any(bit in low for bit in ["api", "graphql", "live", "blog", "story", "feed", "webservice"]):
            if url not in urls:
                urls.append(url)

    for i, url in enumerate(urls[:80], 1):
        print(f"{i:02d}. {url}")

    if not urls:
        print("none")


def main():
    html = fetch(LIVE_URL)
    OUT.write_text(html, encoding="utf-8")

    print(f"Saved CNBC live story HTML to: {OUT}")
    print(f"HTML length: {len(html):,}")

    print_locator_hits(html)

    objects = extract_json_objects_from_live_page(html)

    candidates = []
    seen = set()

    for root_index, root in enumerate(objects, 1):
        for node in walk(root):
            if not isinstance(node, dict):
                continue

            title = best_title(node)
            if not title:
                continue

            key = (title, node_type_text(node))
            if key in seen:
                continue
            seen.add(key)

            candidates.append({
                "root": root_index,
                "type": node_type_text(node),
                "title": title,
                "bad": is_bad_live_candidate(title, node),
            })

    print("")
    print("LIVE PAGE JSON TITLE CANDIDATES")
    print("=" * 100)

    selected = None

    for i, cand in enumerate(candidates[:120], 1):
        status = "SKIP" if cand["bad"] else "KEEP"
        print(f'{i:02d}. {status}: "{cand["title"]}"')
        print(f'    root: {cand["root"]} | type: {cand["type"]}')

        if selected is None and not cand["bad"]:
            selected = cand

    print_api_like_urls(html)

    print("")
    print("=" * 100)

    if selected:
        print(f'1. CNBC: "{selected["title"]}"')
        print("SOURCE: live story page JSON structural candidate")
    else:
        print('1. CNBC: "ERROR: no usable CNBC live-story headline found"')
        print("SOURCE: none")

    print("=" * 100)


if __name__ == "__main__":
    main()
