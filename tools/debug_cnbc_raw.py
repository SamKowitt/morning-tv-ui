import re
import ssl
import urllib.error
import urllib.request
from html import unescape
from pathlib import Path

URL = "https://www.cnbc.com/"
OUT = Path("tools/cnbc_homepage_raw.html")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

SEARCH_TERMS = [
    "Fed meeting live updates",
    "Kevin Warsh",
    "first rate decision",
    "rate decision",
    "Fed meeting",
    "Warsh",
]

ARTICLE_URL_RE = re.compile(
    r'https?://www\.cnbc\.com/20\d{2}/\d{2}/\d{2}/[^"\\<> ]+?\.html'
)

TITLE_RE = re.compile(
    r'"(?:headline|title|name|dek|shorterHeadline|promoTitle)"\s*:\s*"([^"]{20,260})"'
)


def fetch(url):
    req = urllib.request.Request(url, headers=HEADERS)

    # Use relaxed SSL immediately because your Python install is failing certificate validation.
    ctx = ssl._create_unverified_context()

    with urllib.request.urlopen(req, timeout=20, context=ctx) as resp:
        return resp.read().decode("utf-8", errors="replace")


def clean(s):
    s = unescape(s)
    s = s.encode("utf-8").decode("unicode_escape", errors="ignore")
    s = re.sub(r"<[^>]+>", " ", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def print_context(label, html, idx, window=2200):
    start = max(0, idx - window)
    end = min(len(html), idx + window)
    snippet = clean(html[start:end])

    print("\n" + "=" * 120)
    print(label)
    print("=" * 120)
    print(snippet[:4200])


def main():
    html = fetch(URL)
    OUT.write_text(html, encoding="utf-8")

    print(f"Saved raw CNBC homepage HTML to: {OUT}")
    print(f"HTML length: {len(html):,}")

    print("\n" + "#" * 120)
    print("1) EXACT / NEAR EXPECTED HEADLINE SEARCH")
    print("#" * 120)

    lower_html = html.lower()

    for term in SEARCH_TERMS:
        idx = lower_html.find(term.lower())
        if idx >= 0:
            print_context(f'FOUND TERM: "{term}" at index {idx}', html, idx)
        else:
            print(f'NOT FOUND: "{term}"')

    print("\n" + "#" * 120)
    print("2) FIRST 80 CNBC ARTICLE URLS IN RAW HOMEPAGE ORDER")
    print("#" * 120)

    seen_urls = []
    for match in ARTICLE_URL_RE.finditer(html):
        url = match.group(0).replace("\\/", "/")
        if url not in seen_urls:
            seen_urls.append(url)
        if len(seen_urls) >= 80:
            break

    for i, url in enumerate(seen_urls, 1):
        print(f"{i:02d}. {url}")

    print("\n" + "#" * 120)
    print("3) FIRST 120 TITLE-LIKE JSON FIELDS IN RAW HOMEPAGE ORDER")
    print("#" * 120)

    seen_titles = []
    for match in TITLE_RE.finditer(html):
        title = clean(match.group(1))
        if title and title not in seen_titles and len(title) > 12:
            seen_titles.append(title)
        if len(seen_titles) >= 120:
            break

    for i, title in enumerate(seen_titles, 1):
        print(f'{i:02d}. "{title}"')

    print("\n" + "#" * 120)
    print("4) SEARCH AROUND CNBC DATA MARKERS")
    print("#" * 120)

    markers = [
        "__NEXT_DATA__",
        "pageData",
        "assetList",
        "relatedContent",
        "shorterHeadline",
        "promoTitle",
        "headline",
        "Fed meeting live updates",
        "Kevin Warsh",
    ]

    printed = 0
    for marker in markers:
        pos = 0
        while True:
            idx = html.find(marker, pos)
            if idx == -1:
                break

            print_context(f'MARKER: "{marker}" at index {idx}', html, idx, window=1400)
            printed += 1
            pos = idx + len(marker)

            if printed >= 14:
                break

        if printed >= 14:
            break

    print("\n" + "#" * 120)
    print("DONE")
    print("#" * 120)


if __name__ == "__main__":
    main()
