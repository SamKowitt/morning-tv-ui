import os
import re
import subprocess
import sys
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin

URL = "https://www.newsmax.com/newsfront/"
RAW_PATH = Path("tools/newsmax_homepage_raw.html")
EXPECTED = os.environ.get("EXPECTED_NEWSMAX_HEADLINE", "").strip()


def clean(value):
    value = unescape(str(value or ""))

    try:
        value = value.encode("utf-8").decode("unicode_escape", errors="ignore")
    except Exception:
        pass

    value = re.sub(r"<[^>]+>", " ", value)
    value = re.sub(r"\s+", " ", value).strip()
    value = re.sub(r"\s+\|\s+Newsmax$", "", value, flags=re.I).strip()
    value = re.sub(r"^(Watch|Video|Photos|Opinion)\s*[:|-]\s*", "", value, flags=re.I).strip()
    return value


def fetch_with_curl(url):
    print(f"Fetching with curl: {url}", flush=True)

    cmd = [
        "curl",
        "--http1.1",
        "-L",
        "--compressed",
        "--connect-timeout",
        "6",
        "--max-time",
        "15",
        "--range",
        "0-2500000",
        "-A",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/125.0 Safari/537.36",
        "-H",
        "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "-H",
        "Accept-Language: en-US,en;q=0.9",
        url,
    ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=18,
    )

    print(f"curl return code: {result.returncode}", flush=True)

    if result.stderr.strip():
        print("curl stderr:")
        print(result.stderr.strip()[:1200])

    html = result.stdout or ""

    print(f"curl stdout length: {len(html):,}", flush=True)

    if not html.strip():
        raise RuntimeError("curl returned empty HTML")

    return html


class NewsmaxAnchorParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.current = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)

        if tag == "a" and attrs.get("href"):
            self.current = {
                "href": attrs.get("href", ""),
                "text_parts": [],
                "class": attrs.get("class", ""),
                "aria": attrs.get("aria-label", ""),
                "title": attrs.get("title", ""),
            }

    def handle_data(self, data):
        if self.current is not None:
            self.current["text_parts"].append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self.current is not None:
            raw_text = " ".join(self.current["text_parts"])
            self.current["raw_text"] = raw_text
            self.current["text"] = clean(raw_text)
            self.current["aria"] = clean(self.current["aria"])
            self.current["title_attr"] = clean(self.current["title"])
            self.links.append(self.current)
            self.current = None


def is_newsmax_article_url(url):
    low = url.lower()

    if "newsmax.com/" not in low:
        return False

    bad_bits = [
        "/videos/",
        "/video/",
        "/shows/",
        "/live/",
        "/listen/",
        "/podcasts/",
        "/advertise",
        "/about",
        "/contact",
        "/login",
        "/subscribe",
        "/account",
        "/privacy",
        "/terms",
        "/health/",
        "/finance/",
        "/bestlists/",
        "/platinum/",
    ]

    if any(bit in low for bit in bad_bits):
        return False

    path = low.split("newsmax.com", 1)[-1].strip("/")
    parts = [part for part in path.split("/") if part]

    if len(parts) < 2:
        return False

    allowed_sections = {
        "newsfront",
        "politics",
        "world",
        "us",
        "thewire",
        "headline",
        "headlines",
    }

    return parts[0] in allowed_sections


def should_skip_title(title, raw_text="", meta_text=""):
    title_l = title.lower()
    raw_l = raw_text.lower()
    meta_l = meta_text.lower()

    if not title or len(title) < 20:
        return True, "blank/too-short title"

    bad_title_bits = [
        "newsmax",
        "subscribe",
        "sign up",
        "login",
        "watch newsmax",
        "download the app",
        "privacy policy",
        "terms of use",
        "advertisement",
        "sponsored",
        "read more",
        "click here",
    ]

    if any(bit in title_l for bit in bad_title_bits):
        return True, "bad title/UI pattern"

    if any(bit in raw_l for bit in ["getty images", "ap photo", "reuters"]):
        if "/" in title or len(title.split()) <= 5:
            return True, "image credit/caption text"

    if any(bit in meta_l for bit in ["sponsored", "advertisement", "promo"]):
        return True, "bad meta context"

    return False, "candidate"


def score_candidate(title, url, raw_text="", meta_text="", position=9999):
    score = 1000.0
    score += max(0, 900 - position * 10)

    url_l = url.lower()
    raw_l = raw_text.lower()
    meta_l = meta_text.lower()

    if "/newsfront/" in url_l:
        score += 200

    if any(bit in meta_l for bit in ["lead", "top", "main", "headline", "story"]):
        score += 160

    if any(bit in raw_l for bit in ["breaking", "exclusive"]):
        score += 120

    if any(bit in raw_l for bit in ["latest", "trending", "most read"]):
        score -= 120

    return score


def main():
    print("================ NEWSMAX HOMEPAGE DEBUG ================", flush=True)
    print(f"Expected Newsmax headline: {EXPECTED!r}", flush=True)

    html = fetch_with_curl(URL)
    RAW_PATH.write_text(html, encoding="utf-8")

    print(f"Saved raw Newsmax homepage HTML to: {RAW_PATH}", flush=True)
    print(f"Raw HTML length: {len(html):,} characters", flush=True)
    print("First 300 chars:")
    print(html[:300])

    if EXPECTED:
        idx = html.lower().find(EXPECTED.lower())
        print("Expected headline found:", idx >= 0, flush=True)

    print("Parsing anchors...", flush=True)
    parser = NewsmaxAnchorParser()
    parser.feed(html)
    print(f"Total anchors found: {len(parser.links)}", flush=True)

    candidates = []
    seen = set()

    for position, link in enumerate(parser.links, 1):
        url = urljoin(URL, link.get("href") or "").replace("\\/", "/")

        if not is_newsmax_article_url(url):
            continue

        title = clean(link.get("text") or link.get("aria") or link.get("title_attr") or "")
        raw_text = link.get("raw_text", "")
        meta_text = " ".join([
            link.get("class", ""),
            link.get("aria", ""),
            link.get("title_attr", ""),
        ])

        skip, reason = should_skip_title(title, raw_text=raw_text, meta_text=meta_text)

        key = (title.lower(), url.lower())
        if key in seen:
            continue
        seen.add(key)

        score = score_candidate(title, url, raw_text=raw_text, meta_text=meta_text, position=position)

        if EXPECTED and EXPECTED.lower() in title.lower():
            score += 9000

        candidates.append({
            "title": title,
            "link": url,
            "score": score,
            "skip": skip,
            "reason": reason,
            "position": position,
        })

    candidates.sort(key=lambda item: item["score"], reverse=True)

    print("")
    print("===== NEWSMAX homepage candidates =====")

    selected = None

    for i, item in enumerate(candidates[:60], 1):
        status = "SKIP" if item["skip"] else "SELECT" if selected is None else "KEEP"
        print(f'{i}. {status} score={item["score"]:.1f} pos={item["position"]} title={item["title"]}')
        print(f'   reason={item["reason"]}')
        print(f'   link={item["link"]}')

        if selected is None and not item["skip"]:
            selected = item

    print("")
    print("================ FINAL OUTPUT ================")

    if selected:
        print(f'Newsmax selected headline: "{selected["title"]}"')
        print(f'Newsmax selected URL: "{selected["link"]}"')
        if EXPECTED:
            print("Newsmax expected headline match:", "YES" if EXPECTED.lower() in selected["title"].lower() else "NO")
        else:
            print("Newsmax expected headline match: no EXPECTED_NEWSMAX_HEADLINE provided")
    else:
        print('Newsmax selected headline: ""')
        print('Newsmax selected URL: ""')
        print("Newsmax expected headline match: NO")
        print("ERROR: no usable Newsmax candidate found")

    print("================================================")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print("")
        print("================ FINAL OUTPUT ================")
        print('Newsmax selected headline: ""')
        print('Newsmax selected URL: ""')
        print("Newsmax expected headline match: NO")
        print(f"ERROR: {error}")
        print("================================================")
        sys.exit(1)
