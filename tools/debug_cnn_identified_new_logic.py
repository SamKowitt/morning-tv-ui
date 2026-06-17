import re
import ssl
import urllib.request
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin

CNN_HOME = "https://www.cnn.com/"
RAW_PATH = Path("tools/cnn_homepage_raw.html")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


def fetch_url(url):
    req = urllib.request.Request(url, headers=HEADERS)
    ctx = ssl._create_unverified_context()
    with urllib.request.urlopen(req, timeout=20, context=ctx) as resp:
        return resp.read().decode("utf-8", errors="replace")


def clean(value):
    value = unescape(str(value or ""))

    replacements = {
        "Ã¢Â€Â™": "'",
        "Ã¢Â€Â˜": "'",
        "Ã¢Â€Âœ": '"',
        "Ã¢Â€Â": '"',
        "Ã¢Â€Â�": '"',
        "Ã¢Â�Â�": '"',
        "Ã¢Â�Â¢": "•",
        "Ã¢Â€Â¢": "•",
    }

    for bad, good in replacements.items():
        value = value.replace(bad, good)

    value = re.sub(r"<[^>]+>", " ", value)
    value = re.sub(r"\s+", " ", value).strip()

    value = re.sub(r"\s+Show\s+all\s*$", "", value, flags=re.I).strip()
    value = re.sub(r"^•\s*", "", value).strip()
    value = re.sub(r"^(Breaking News|Analysis|Video|CNN Exclusive|For Subscribers)\s+", "", value, flags=re.I).strip()

    return value


class CNNAnchorParser(HTMLParser):
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
                "data": " ".join(f"{k}={v}" for k, v in attrs.items() if k.startswith("data-")),
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
            self.links.append(self.current)
            self.current = None


def is_cnn_article_url(url):
    low = url.lower()

    if "cnn.com/202" not in low:
        return False

    bad_bits = [
        "/videos/",
        "/audio/",
        "/podcasts/",
        "/cnn-underscored/",
        "/style/",
        "/travel/",
        "/entertainment/",
        "/weather/",
        "/interactive/",
        "/live-news/",
    ]

    return not any(bit in low for bit in bad_bits)


def should_skip_title(title, url, raw_text="", meta_text=""):
    title_l = title.lower()
    url_l = url.lower()
    raw_l = raw_text.lower()
    meta_l = meta_text.lower()

    if not title or len(title) < 20:
        return True, "blank/too-short title"

    if title_l in {"trending primary results", "obtained from social media"}:
        return True, "navigation/UI text"

    bad_title_bits = [
        "all there is with anderson cooper",
        "chasing life with dr. sanjay gupta",
        "the assignment with audie cornish",
        "cnn underscored",
        "newsletter",
        "subscribe",
        "sign up",
        "listen to",
        "watch:",
        "video ",
        "video:",
        "photos:",
        "for subscribers",
        "paid content",
        "advertisement",
        "getty images",
        "afp/getty",
        "ap photo",
        "reuters",
        "bloomberg/getty",
        "/ap",
        "/getty",
        "nikhinson/ap",
        "read the whole",
    ]

    if any(bit in title_l for bit in bad_title_bits):
        return True, "bad title/caption/UI pattern"

    # Reject image-credit/caption-only anchors.
    credit_patterns = [
        r"^[A-Z][A-Za-z .'-]+/[A-Z]{2,}$",
        r"^[A-Z][A-Za-z .'-]+/(AP|Reuters|Getty Images|AFP|Bloomberg)(/Getty Images)?$",
        r"^[A-Z][A-Za-z .'-]+\s*/\s*(AP|Reuters|Getty Images|AFP|Bloomberg)",
    ]

    for pattern in credit_patterns:
        if re.search(pattern, title, flags=re.I):
            return True, "image credit/caption text"

    if any(bit in raw_l for bit in ["getty images", "afp/getty", "ap photo", "reuters", "bloomberg/getty"]):
        # Only skip if the cleaned title itself looks like a credit/caption, not if the full card includes one.
        if "/" in title or len(title.split()) <= 5:
            return True, "raw caption/source text"

    bad_meta_bits = [
        "podcast",
        "audio",
        "cnn underscored",
        "paid content",
        "sponsored",
        "newsletter",
    ]

    if any(bit in meta_l for bit in bad_meta_bits):
        return True, "bad module/meta context"

    if any(bit in url_l for bit in ["/audio/", "/podcasts/", "/cnn-underscored/", "/videos/"]):
        return True, "bad URL type"

    return False, "candidate"


def score_candidate(cand):
    score = 0
    raw_l = cand["raw_text"].lower()
    title_l = cand["title"].lower()
    meta_l = cand["meta"].lower()

    # Structural homepage lead-package signals.
    if "show all" in raw_l:
        score += 1000
    if "breaking news" in raw_l:
        score += 600
    if "container__headline" in meta_l or "headline" in meta_l:
        score += 200

    # Prefer article-like headline length, not captions or tiny labels.
    if 25 <= len(cand["title"]) <= 95:
        score += 100

    # Penalize UI/secondary cards.
    if title_l.startswith(("trump ", "video ", "analysis ", "cnn poll ")):
        score -= 50

    # Preserve homepage order as tie breaker.
    score -= cand["position"] * 0.01

    return score


def anchor_candidates(html):
    parser = CNNAnchorParser()
    parser.feed(html)

    candidates = []
    seen = set()
    position = 0

    for link in parser.links:
        url = urljoin(CNN_HOME, link["href"]).split("?")[0].split("#")[0]

        if not is_cnn_article_url(url):
            continue

        raw_text = link.get("raw_text", "")
        title = clean(link["aria"] or link["text"])

        key = (url, title)
        if key in seen:
            continue
        seen.add(key)

        position += 1

        meta = " ".join([link.get("class", ""), link.get("data", "")])
        skip, reason = should_skip_title(title, url, raw_text, meta)

        cand = {
            "position": position,
            "title": title,
            "url": url,
            "skip": skip,
            "reason": reason,
            "meta": meta,
            "raw_text": raw_text,
            "score": 0,
        }

        if not skip:
            cand["score"] = score_candidate(cand)

        candidates.append(cand)

    return candidates


def main():
    html = fetch_url(CNN_HOME)
    RAW_PATH.write_text(html, encoding="utf-8")

    candidates = anchor_candidates(html)

    print("")
    print("CNN ANCHOR CANDIDATES CHECKED")
    print("=" * 100)

    for cand in candidates[:80]:
        status = "SKIP" if cand["skip"] else "KEEP"
        print(f'{cand["position"]:02d}. {status}: "{cand["title"]}"')
        print(f'    score: {cand["score"]:.2f}')
        print(f'    reason: {cand["reason"]}')
        print(f'    url: {cand["url"]}')

    keepers = [c for c in candidates if not c["skip"]]
    selected = max(keepers, key=lambda c: c["score"]) if keepers else None

    print("")
    print("=" * 100)

    if selected:
        print(f'1. CNN: "{selected["title"]}"')
        print(f'URL: {selected["url"]}')
        print(f'POSITION: {selected["position"]}')
        print(f'SCORE: {selected["score"]:.2f}')
    else:
        print('1. CNN: "ERROR: no usable CNN candidate found"')

    print("=" * 100)


if __name__ == "__main__":
    main()
