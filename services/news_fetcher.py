import html
import json
import os
import re
import ssl
import time
import threading
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from difflib import SequenceMatcher

import certifi
from services.article_text_fetcher import prefetch_article_text_payload
from services.newsmax_chrome import (
    fetch_newsmax_homepage_article,
    fetch_newsmax_image_jpeg_bytes,
)


@dataclass
class NewsArticle:
    title: str
    source: str
    image_url: str = ""
    link: str = ""
    image_bytes: bytes = b""
    breaking_headline: str = ""


SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())

REQUEST_TIMEOUT = 4
RSS_TIMEOUT = 3
IMAGE_PAGE_TIMEOUT = 2
IMAGE_DOWNLOAD_TIMEOUT = 2

CACHE_FILE = os.path.expanduser("~/.morning_tv_ui_news_cache.json")

FOX_HOMEPAGE = "https://www.foxnews.com/"
CNBC_HOMEPAGE = "https://www.cnbc.com/"

FOX_FEEDS = [
    "https://feeds.foxnews.com/foxnews/latest?format=xml",
    "https://moxie.foxnews.com/google-publisher/latest.xml",
]

CNBC_FEEDS = [
    "https://www.cnbc.com/id/100003114/device/rss/rss.html",
    "https://www.cnbc.com/id/15837362/device/rss/rss.html",
    "https://www.cnbc.com/id/20910258/device/rss/rss.html",
]

NEWS_SOURCES = {
    "FOX": {
        "dropdown": "FoxNews.com",
        "source_name": "FOX NEWS",
        "homepage": FOX_HOMEPAGE,
        "allowed_domain": "foxnews.com",
        "feeds": FOX_FEEDS,
        "prefer_homepage_first": True,
    },
    "CNBC": {
        "dropdown": "CNBC.com",
        "source_name": "CNBC",
        "homepage": CNBC_HOMEPAGE,
        "allowed_domain": "cnbc.com",
        "feeds": CNBC_FEEDS,
        "prefer_homepage_first": True,
    },
    "CNN": {
        "dropdown": "CNN.com",
        "source_name": "CNN",
        "homepage": "https://www.cnn.com/",
        "allowed_domain": "cnn.com",
        "feeds": [
            "https://rss.cnn.com/rss/cnn_topstories.rss",
            "https://rss.cnn.com/rss/edition.rss",
        ],
    },
    "BLOOMBERG": {
        "dropdown": "Bloomberg.com",
        "source_name": "BLOOMBERG",
        "homepage": "https://www.bloomberg.com/",
        "allowed_domain": "bloomberg.com",
        "feeds": [
            "https://feeds.bloomberg.com/markets/news.rss",
            "https://feeds.bloomberg.com/politics/news.rss",
        ],
    },
    "NEWSMAX": {
        "dropdown": "Newsmax.com",
        "source_name": "NEWSMAX",
        "homepage": "https://www.newsmax.com/",
        "allowed_domain": "newsmax.com",
        "feeds": [
            "https://www.newsmax.com/rss/Newsfront/16/",
            "https://www.newsmax.com/rss/Politics/1/",
        ],
        "prefer_homepage_first": True,
    },
    "NYTIMES": {
        "dropdown": "NYtimes.com",
        "source_name": "NY TIMES",
        "homepage": "https://www.nytimes.com/",
        "allowed_domain": "nytimes.com",
        "feeds": [
            "https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml",
            "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
        ],
    },
    "REUTERS": {
        "dropdown": "Reuters.com",
        "source_name": "REUTERS",
        "homepage": "https://www.reuters.com/",
        "allowed_domain": "reuters.com",
        "feeds": [
            "https://www.reutersagency.com/feed/?best-topics=top-news&post_type=best",
            "https://feeds.reuters.com/reuters/topNews",
        ],
    },
    "TIMESOFISRAEL": {
        "dropdown": "TimesofIsrael.com",
        "source_name": "TIMES OF ISRAEL",
        "homepage": "https://www.timesofisrael.com/",
        "allowed_domain": "timesofisrael.com",
        "feeds": [
            "https://www.timesofisrael.com/feed/",
        ],
        "prefer_homepage_first": True,
    },
    "BBC": {
        "dropdown": "BBC.com",
        "source_name": "BBC",
        "homepage": "https://www.bbc.com/news",
        "allowed_domain": "bbc.com",
        "feeds": [
            "https://feeds.bbci.co.uk/news/rss.xml",
            "https://feeds.bbci.co.uk/news/world/rss.xml",
        ],
    },
    "APNEWS": {
        "dropdown": "Apnews.com",
        "source_name": "AP NEWS",
        "homepage": "https://apnews.com/",
        "allowed_domain": "apnews.com",
        "feeds": [
            "https://apnews.com/hub/ap-top-news?output=rss",
        ],
    },
}

EXPECTED_HEADLINES = {}

NEWS_SOURCE_OPTIONS = [(key, value["dropdown"]) for key, value in NEWS_SOURCES.items()]


@dataclass
class Candidate:
    title: str
    source: str
    image_url: str = ""
    link: str = ""
    origin: str = ""
    position: int = 999999
    score: float = 0.0


def get_news_source_display(source_key):
    config = NEWS_SOURCES.get(source_key, NEWS_SOURCES["FOX"])
    return config["source_name"]


def get_news_source_name(source_key):
    return get_news_source_display(source_key)


def fetch_url_bytes(url, timeout=REQUEST_TIMEOUT):
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0 Safari/537.36"
            ),
            "Accept": (
                "text/html,application/xhtml+xml,application/xml;q=0.9,"
                "image/avif,image/webp,image/apng,*/*;q=0.8"
            ),
            "Accept-Language": "en-US,en;q=0.9",
            "Connection": "keep-alive",
        },
    )

    with urllib.request.urlopen(
        request,
        timeout=timeout,
        context=SSL_CONTEXT,
    ) as response:
        return response.read(), response.headers.get("Content-Type", "")



def fetch_url_text(url, timeout=REQUEST_TIMEOUT):
    data, _ = fetch_url_bytes(url, timeout=timeout)
    return data.decode("utf-8", errors="ignore")


def clean_text(value):
    if not value:
        return ""

    value = html.unescape(str(value))
    value = re.sub(r"<script.*?</script>", "", value, flags=re.IGNORECASE | re.DOTALL)
    value = re.sub(r"<style.*?</style>", "", value, flags=re.IGNORECASE | re.DOTALL)
    value = re.sub(r"<[^>]+>", " ", value)
    value = re.sub(r"\s+", " ", value).strip()
    value = re.sub(
        r"\s+(show all|read more|see more|view more|show more)$",
        "",
        value,
        flags=re.IGNORECASE,
    ).strip()

    return value


def normalize_text(value):
    value = clean_text(value).lower()
    value = value.replace("u.s.", "us")
    value = value.replace("u.s", "us")
    value = value.replace("’", "'")
    value = re.sub(r"[^a-z0-9]+", " ", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value


def absolute_url(base_url, maybe_url):
    if not maybe_url:
        return ""

    return urllib.parse.urljoin(base_url, html.unescape(str(maybe_url)))


def is_reasonable_headline(title):
    if not title:
        return False

    title_lower = title.lower()

    blocked = [
        "subscribe",
        "sign in",
        "watch live",
        "menu",
        "search",
        "markets",
        "weather",
        "newsletters",
        "privacy",
        "terms",
        "advertise",
        "contact",
        "tv schedule",
        "listen",
        "live tv",
        "skip navigation",
        "sponsored",
        "advertisement",
    ]

    if any(word in title_lower for word in blocked):
        return False

    if len(title) < 18:
        return False

    if len(title.split()) < 4:
        return False

    return True


def find_meta_content(page_html, names):
    for name in names:
        patterns = [
            rf'<meta[^>]+property=["\']{re.escape(name)}["\'][^>]+content=["\']([^"\']+)["\']',
            rf'<meta[^>]+name=["\']{re.escape(name)}["\'][^>]+content=["\']([^"\']+)["\']',
            rf'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']{re.escape(name)}["\']',
            rf'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']{re.escape(name)}["\']',
        ]

        for pattern in patterns:
            match = re.search(pattern, page_html, re.IGNORECASE)
            if match:
                return html.unescape(match.group(1)).strip()

    return ""


def extract_json_ld_objects(page_html):
    objects = []

    scripts = re.findall(
        r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        page_html,
        flags=re.IGNORECASE | re.DOTALL,
    )

    for script in scripts:
        raw = html.unescape(script).strip()

        try:
            parsed = json.loads(raw)
            objects.append(parsed)
        except Exception:
            continue

    return objects


def flatten_json_objects(value):
    found = []

    if isinstance(value, dict):
        found.append(value)

        for child in value.values():
            found.extend(flatten_json_objects(child))

    elif isinstance(value, list):
        for child in value:
            found.extend(flatten_json_objects(child))

    return found


def get_image_from_json_value(value):
    if not value:
        return ""

    if isinstance(value, str):
        return value

    if isinstance(value, dict):
        return value.get("url", "") or value.get("contentUrl", "")

    if isinstance(value, list) and value:
        return get_image_from_json_value(value[0])

    return ""


def extract_homepage_candidates_from_json_ld(page_html, base_url, source_name):
    candidates = []

    for root_object in extract_json_ld_objects(page_html):
        for obj in flatten_json_objects(root_object):
            obj_type = obj.get("@type", "")

            if isinstance(obj_type, list):
                obj_type_text = " ".join(obj_type)
            else:
                obj_type_text = str(obj_type)

            if not any(
                key in obj_type_text.lower()
                for key in ["newsarticle", "article", "reportagenewsarticle", "liveblogposting"]
            ):
                continue

            title = clean_text(
                obj.get("headline", "")
                or obj.get("name", "")
                or obj.get("title", "")
            )

            link_value = obj.get("url", "") or obj.get("mainEntityOfPage", "")
            if isinstance(link_value, dict):
                link_value = link_value.get("@id", "") or link_value.get("url", "")

            link = absolute_url(base_url, link_value)
            image_url = absolute_url(base_url, get_image_from_json_value(obj.get("image", "")))

            if is_reasonable_headline(title):
                candidates.append(
                    Candidate(
                        title=title,
                        source=source_name,
                        image_url=image_url,
                        link=link,
                        origin="homepage_json_ld",
                        position=len(candidates),
                    )
                )

    return candidates


def extract_homepage_candidates_from_links(page_html, base_url, allowed_domain_text, source_name):
    candidates = []

    article_blocks = re.finditer(
        r'<a\s+[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',
        page_html,
        flags=re.IGNORECASE | re.DOTALL,
    )

    seen_titles = set()

    for match in article_blocks:
        href = match.group(1)
        inner_html = match.group(2)

        link = absolute_url(base_url, href)
        title = clean_text(inner_html)

        if allowed_domain_text not in link:
            continue

        if not is_reasonable_headline(title):
            continue

        key = normalize_text(title)
        if key in seen_titles:
            continue

        seen_titles.add(key)

        candidates.append(
            Candidate(
                title=title,
                source=source_name,
                image_url="",
                link=link,
                origin="homepage_anchor",
                position=match.start(),
            )
        )

    return candidates


def decode_jsonish_string(value):
    if not value:
        return ""

    try:
        return json.loads(f'"{value}"')
    except Exception:
        return html.unescape(value).replace("\\/", "/").replace('\\"', '"').strip()


def extract_json_string_field(chunk, field_names):
    for field_name in field_names:
        pattern = rf'"{re.escape(field_name)}"\s*:\s*"((?:\\.|[^"\\])*)"'
        match = re.search(pattern, chunk, re.IGNORECASE | re.DOTALL)

        if match:
            return clean_text(decode_jsonish_string(match.group(1)))

    return ""


def extract_embedded_json_candidates(page_html, base_url, allowed_domain_text, source_name):
    candidates = []
    object_pattern = re.compile(r"\{[^{}]{0,9000}\}", re.DOTALL)

    for match in object_pattern.finditer(page_html):
        chunk = match.group(0)

        title = extract_json_string_field(
            chunk,
            [
                "headline",
                "title",
                "shorterHeadline",
                "promoHeadline",
                "cardTitle",
                "name",
                "dek",
            ],
        )

        link = extract_json_string_field(
            chunk,
            [
                "url",
                "link",
                "webUrl",
                "nativeUrl",
                "path",
                "canonicalUrl",
            ],
        )

        image_url = extract_json_string_field(
            chunk,
            [
                "image",
                "imageUrl",
                "promoImageUrl",
                "thumbnail",
                "thumbnailUrl",
                "contentUrl",
            ],
        )

        if not title or not link:
            continue

        if not is_reasonable_headline(title):
            continue

        link = absolute_url(base_url, link)
        image_url = absolute_url(base_url, image_url)

        if allowed_domain_text not in link:
            continue

        if "/video/" in link or "/watch/" in link:
            continue

        candidates.append(
            Candidate(
                title=title,
                source=source_name,
                image_url=image_url,
                link=link,
                origin="homepage_embedded_json",
                position=match.start(),
            )
        )

    return candidates


def get_child_raw_text(item, tag_name):
    for child in item:
        if child.tag.lower().endswith(tag_name.lower()):
            return child.text or ""

    return ""


def find_child_text(item, tag_name):
    return clean_text(get_child_raw_text(item, tag_name))


def find_rss_image_url(item):
    for child in item:
        tag = child.tag.lower()

        if tag.endswith("content") or tag.endswith("thumbnail"):
            url = child.attrib.get("url", "")
            medium = child.attrib.get("medium", "")
            content_type = child.attrib.get("type", "")

            if url and (
                "image" in content_type
                or medium == "image"
                or url.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))
            ):
                return url

        if tag.endswith("enclosure"):
            url = child.attrib.get("url", "")
            content_type = child.attrib.get("type", "")

            if url and (
                "image" in content_type
                or url.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))
            ):
                return url

    raw_description = html.unescape(get_child_raw_text(item, "description"))

    image_match = re.search(
        r'<img[^>]+src=["\']([^"\']+)["\']',
        raw_description,
        re.IGNORECASE,
    )

    if image_match:
        return image_match.group(1)

    return ""


def is_bad_market_live_title(title):
    lowered = title.lower()

    blocked_phrases = [
        "stock market today",
        "live updates",
        "stocks end higher",
        "stocks end lower",
        "stock futures",
        "dow futures",
        "nasdaq futures",
        "s&p futures",
        "markets live",
    ]

    return any(phrase in lowered for phrase in blocked_phrases)


def candidate_key(candidate):
    return (
        normalize_text(candidate.title),
        candidate.link.split("?")[0].rstrip("/"),
    )


def dedupe_candidates(candidates):
    seen = set()
    deduped = []

    for candidate in candidates:
        key = candidate_key(candidate)

        if key in seen:
            continue

        seen.add(key)
        deduped.append(candidate)

    return deduped


def target_terms_for_source(source_key):
    return set()


def score_candidate(candidate, source_key):
    title = clean_text(candidate.title)
    normalized_title = normalize_text(title)

    if not normalized_title:
        candidate.score = -10000
        return candidate.score

    score = 0.0

    # Prefer real homepage candidates over RSS when a source exposes them.
    # This avoids stale RSS or old debug-targeted stories beating the current lead card.
    origin = (candidate.origin or "").lower()

    if origin == "homepage_link":
        score += 1200
    elif origin == "homepage_embedded_json":
        score += 1050
    elif origin == "homepage_json_ld":
        score += 850
    elif origin.startswith("homepage"):
        score += 800
    elif origin.startswith("rss"):
        score += 350

    # Earlier page/feed position should win within the same source type.
    score += max(0, 100000 - min(candidate.position, 100000)) / 100.0

    # Actual article-ish signals.
    if candidate.link:
        score += 40

    if candidate.image_url:
        score += 25

    # Penalize known non-headline/site furniture/live-market junk.
    if is_bad_market_live_title(candidate.title):
        score -= 600

    lowered = normalized_title
    junk_terms = [
        "watch live",
        "live updates",
        "newsletter",
        "subscribe",
        "opinion",
        "video",
        "photos",
        "weather",
        "stock market today",
    ]

    for term in junk_terms:
        if term in lowered:
            score -= 120

    candidate.score = score
    return score


def print_candidate_debug(source_key, candidates, label):
    source_name = get_news_source_display(source_key)
    scored = sorted(candidates, key=lambda item: score_candidate(item, source_key), reverse=True)

    print(f"\n===== {source_name} {label} candidates =====")
    print(f"Expected: {EXPECTED_HEADLINES.get(source_key, '')}")

    if not scored:
        print("No candidates found.")
        return

    for index, candidate in enumerate(scored[:8], start=1):
        print(
            f"{index}. score={candidate.score:.1f} origin={candidate.origin} "
            f"title={candidate.title}"
        )
        if candidate.link:
            print(f"   link={candidate.link}")


def fetch_reuters_url_text(url, timeout=REQUEST_TIMEOUT):
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0.0.0 Safari/537.36"
            ),
            "Accept": (
                "text/html,application/xhtml+xml,application/xml;q=0.9,"
                "image/avif,image/webp,image/apng,*/*;q=0.8"
            ),
            "Accept-Language": "en-US,en;q=0.9",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "Connection": "keep-alive",
        },
    )

    relaxed_context = ssl._create_unverified_context()

    with urllib.request.urlopen(
        request,
        timeout=timeout,
        context=relaxed_context,
    ) as response:
        return response.read().decode("utf-8", errors="ignore")


def fetch_homepage_candidates(source_key):
    config = NEWS_SOURCES[source_key]
    source_name = config["source_name"]
    homepage_url = config["homepage"]
    allowed_domain_text = config["allowed_domain"]

    print(f"Trying {source_name} homepage: {homepage_url}")

    if source_key == "REUTERS":
        page_html = fetch_reuters_url_text(homepage_url, timeout=REQUEST_TIMEOUT)
    else:
        page_html = fetch_url_text(homepage_url, timeout=REQUEST_TIMEOUT)

    candidates = []
    candidates.extend(
        extract_homepage_candidates_from_json_ld(
            page_html=page_html,
            base_url=homepage_url,
            source_name=source_name,
        )
    )
    candidates.extend(
        extract_embedded_json_candidates(
            page_html=page_html,
            base_url=homepage_url,
            allowed_domain_text=allowed_domain_text,
            source_name=source_name,
        )
    )
    candidates.extend(
        extract_homepage_candidates_from_links(
            page_html=page_html,
            base_url=homepage_url,
            allowed_domain_text=allowed_domain_text,
            source_name=source_name,
        )
    )

    return dedupe_candidates(candidates)


def fetch_rss_article_candidates(feed_url, source_name, timeout=RSS_TIMEOUT):
    request = urllib.request.Request(
        feed_url,
        headers={
            "User-Agent": "Mozilla/5.0 MorningTVUI/1.0",
            "Accept": "application/rss+xml, application/xml, text/xml, */*",
        },
    )

    with urllib.request.urlopen(
        request,
        timeout=timeout,
        context=SSL_CONTEXT,
    ) as response:
        xml_data = response.read()

    root = ET.fromstring(xml_data)
    items = root.findall(".//item")

    candidates = []

    for position, item in enumerate(items):
        title = find_child_text(item, "title")
        link = find_child_text(item, "link")
        image_url = find_rss_image_url(item)

        if not title:
            continue

        if is_bad_market_live_title(title):
            continue

        candidates.append(
            Candidate(
                title=title,
                source=source_name,
                image_url=image_url,
                link=link,
                origin="rss",
                position=position,
            )
        )

    return candidates


def fetch_rss_candidates(source_key):
    config = NEWS_SOURCES[source_key]
    source_name = config["source_name"]
    all_candidates = []

    for feed_url in config.get("feeds", []):
        try:
            print(f"Trying {source_name} RSS feed: {feed_url}")
            feed_candidates = fetch_rss_article_candidates(feed_url, source_name)
            all_candidates.extend(feed_candidates)
        except Exception as error:
            print(f"{source_name} RSS failed: {feed_url} -> {error}")

    return dedupe_candidates(all_candidates)


def find_page_image_url(article_url):
    if not article_url:
        return ""

    try:
        page_html = fetch_url_text(article_url, timeout=IMAGE_PAGE_TIMEOUT)
    except Exception as error:
        print(f"Image page lookup failed: {article_url} -> {error}")
        return ""

    image_url = find_meta_content(
        page_html,
        ["og:image", "twitter:image", "twitter:image:src"],
    )

    return absolute_url(article_url, image_url)


def download_image_bytes(image_url):
    if not image_url:
        return b""

    try:
        data, content_type = fetch_url_bytes(image_url, timeout=IMAGE_DOWNLOAD_TIMEOUT)

        if "image" in content_type.lower() or image_url.lower().endswith(
            (".jpg", ".jpeg", ".png", ".webp")
        ):
            return data

    except Exception as error:
        print(f"Image download failed: {image_url} -> {error}")

    return b""


def enrich_article(article):
    """
    Keep headline fetching fast.

    Images are loaded asynchronously by NewsCard after the dashboard is visible.
    This prevents slow image pages, AVIF conversions, or blocked image hosts from
    delaying the entire news-card request.
    """
    return article


def cache_key(source_key):
    return source_key


def load_cache():
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as file:
            return json.load(file)
    except Exception:
        return {}


def save_cache(cache):
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as file:
            json.dump(cache, file, indent=2)
    except Exception as error:
        print(f"News cache save failed: {error}")


def article_from_cache(source_key):
    # Cache disabled. We do not want an old article from one source
    # showing under a different selected source.
    return None


def cache_article(source_key, article):
    # Cache disabled. Always fetch the selected source fresh.
    return


def fallback_article(source_key, error_message=""):
    source_name = get_news_source_display(source_key)
    cached = article_from_cache(source_key)

    if cached:
        print(f"Using cached {source_name} article after fetch failure: {error_message}")
        return cached

    return NewsArticle(
        title=f"Unable to load latest {source_name} headline.",
        source=source_name,
        image_url="",
        link="",
        image_bytes=b"",
    )


def build_article_from_candidate(candidate):
    return NewsArticle(
        title=candidate.title,
        source=candidate.source,
        image_url=candidate.image_url,
        link=candidate.link,
    )


def choose_best_candidate(source_key, candidates):
    candidates = dedupe_candidates(candidates)

    candidates = [
        candidate for candidate in candidates
        if is_reasonable_headline(candidate.title)
        and not is_bad_market_live_title(candidate.title)
    ]

    if not candidates:
        raise RuntimeError("No usable headline candidates found")

    for candidate in candidates:
        score_candidate(candidate, source_key)

    candidates.sort(key=lambda item: item.score, reverse=True)
    return candidates[0]


def normalize_source_key(source_key):
    source_key = str(source_key or "").strip().upper()

    if source_key not in NEWS_SOURCES:
        print(f"Unknown news source key {source_key}; falling back to FOX NEWS")
        source_key = "FOX"

    return source_key


def fetch_generic_ranked_candidates(source_key):
    source_key = normalize_source_key(source_key)

    config = NEWS_SOURCES[source_key]
    source_name = config["source_name"]

    all_candidates = []
    errors = []

    # For sources where the homepage actually exposes the lead card cleanly, try it
    # first. For others, RSS is usually much faster and less likely to be blocked.
    try_homepage_first = bool(config.get("prefer_homepage_first", False))

    if try_homepage_first:
        try:
            homepage_candidates = fetch_homepage_candidates(source_key)
            print_candidate_debug(source_key, homepage_candidates, "homepage")
            all_candidates.extend(homepage_candidates)
        except Exception as error:
            message = f"homepage -> {error}"
            print(f"{source_name} homepage failed: {error}")
            errors.append(message)

    try:
        rss_candidates = fetch_rss_candidates(source_key)
        print_candidate_debug(source_key, rss_candidates, "RSS")
        all_candidates.extend(rss_candidates)
    except Exception as error:
        message = f"rss -> {error}"
        print(f"{source_name} RSS fetch failed: {error}")
        errors.append(message)

    if not try_homepage_first:
        try:
            homepage_candidates = fetch_homepage_candidates(source_key)
            print_candidate_debug(source_key, homepage_candidates, "homepage")
            all_candidates.extend(homepage_candidates)
        except Exception as error:
            message = f"homepage -> {error}"
            print(f"{source_name} homepage failed: {error}")
            errors.append(message)

    ranked_candidates = dedupe_candidates(all_candidates)

    if not ranked_candidates:
        raise RuntimeError("No usable headline candidates found: " + " | ".join(errors))

    for candidate in ranked_candidates:
        score_candidate(candidate, source_key)

    ranked_candidates.sort(key=lambda item: item.score, reverse=True)

    return source_key, source_name, ranked_candidates


def fetch_configured_article(source_key):
    source_key = normalize_source_key(source_key)

    # Newsmax works through Chrome on this Mac but direct urllib/RSS requests
    # can hang or return incorrect results. Never use the generic route here.
    if source_key == "NEWSMAX":
        try:
            payload = fetch_newsmax_homepage_article()

            article_url = str(payload.get("link", "") or "").strip()
            image_url = str(payload.get("image_url", "") or "").strip()
            image_bytes = b""

            # Use only the image from the same #nmCanvas1 homepage lead module.
            # Do not fall back to the article-page og:image; that can be a
            # different editorial image than the lead-card image.
            if image_url:
                try:
                    image_bytes = fetch_newsmax_image_jpeg_bytes(image_url)

                    if image_bytes:
                        print(
                            "NEWSMAX CANVAS-ONE IMAGE READY: "
                            f"{len(image_bytes)} bytes | {image_url}"
                        )
                    else:
                        print(
                            "NEWSMAX CANVAS-ONE IMAGE NOT READY: "
                            f"no usable JPEG bytes | {image_url}"
                        )

                except Exception as image_error:
                    print(
                        "NEWSMAX canvas-one image fetch failed: "
                        f"{image_error}"
                    )
            else:
                print("NEWSMAX canvas-one lead image was not found.")

            return NewsArticle(
                title=payload.get("title", "") or "",
                source=NEWS_SOURCES["NEWSMAX"]["source_name"],
                image_url=image_url,
                link=article_url,
                image_bytes=image_bytes,
                breaking_headline=payload.get("breaking_headline", "") or "",
            )

        except Exception as error:
            print(f"NEWSMAX Chrome resolver failed: {error}")
            return fallback_article(
                "NEWSMAX",
                "Chrome-backed Newsmax fetch failed: " + str(error),
            )

    if source_key in {"FOX", "CNN"}:
        try:
            payload = fetch_source_specific_homepage_lead_article(source_key)

            # CNN source-specific resolver returns a dict. The UI/news validation code
            # expects the normal article object with .source, .title, .link, etc.
            article = fallback_article(source_key, "")
            article.source = NEWS_SOURCES[source_key]["source_name"]
            article.title = payload.get("title", "") or ""
            article.link = payload.get("link", "") or payload.get("url", "") or ""
            article.summary = payload.get("summary", "") or ""
            article.image_url = payload.get("image", "") or payload.get("image_url", "") or ""
            article.image_bytes = payload.get("image_bytes", b"") or b""

            try:
                article = enrich_article(article)
            except Exception as enrich_error:
                print(f"CNN source-specific article enrich failed: {enrich_error}")

            cache_article(source_key, article)
            return article

        except Exception as error:
            print(f"CNN direct homepage resolver failed: {error}; falling back to generic logic")

    if source_key == "CNBC":
        try:
            return fetch_cnbc_rendered_largest_text_lead_article(source_key)
        except Exception as error:
            print(
                "CNBC rendered-largest-text resolver failed: "
                f"{error}; falling back to existing CNBC resolver"
            )

            try:
                return fetch_cnbc_homepage_lead_article(source_key)
            except Exception as fallback_error:
                print(
                    "CNBC existing homepage resolver failed: "
                    f"{fallback_error}; falling back to generic logic"
                )

    if source_key not in NEWS_SOURCES:
        print(f"Unknown news source key {source_key}; falling back to FOX NEWS")
        source_key = "FOX"

    config = NEWS_SOURCES[source_key]
    source_name = config["source_name"]
    errors = []

    try_homepage_first = bool(config.get("prefer_homepage_first", False))

    if try_homepage_first:
        try:
            homepage_candidates = fetch_homepage_candidates(source_key)
            print_candidate_debug(source_key, homepage_candidates, "homepage")

            if homepage_candidates:
                best_homepage = choose_best_candidate(source_key, homepage_candidates)
                print(
                    f"SELECTED {source_name} HOMEPAGE: score={best_homepage.score:.1f} "
                    f"origin={best_homepage.origin} title={best_homepage.title}"
                )
                article = enrich_article(build_article_from_candidate(best_homepage))
                cache_article(source_key, article)
                return article

        except Exception as error:
            message = f"homepage -> {error}"
            print(f"{source_name} homepage failed: {error}")
            errors.append(message)

    try:
        rss_candidates = fetch_rss_candidates(source_key)
        print_candidate_debug(source_key, rss_candidates, "RSS")

        if rss_candidates:
            best_rss = choose_best_candidate(source_key, rss_candidates)
            print(
                f"SELECTED {source_name} RSS: score={best_rss.score:.1f} "
                f"origin={best_rss.origin} title={best_rss.title}"
            )
            article = enrich_article(build_article_from_candidate(best_rss))
            cache_article(source_key, article)
            return article

    except Exception as error:
        message = f"rss -> {error}"
        print(f"{source_name} RSS fetch failed: {error}")
        errors.append(message)

    if not try_homepage_first:
        try:
            homepage_candidates = fetch_homepage_candidates(source_key)
            print_candidate_debug(source_key, homepage_candidates, "homepage")

            if homepage_candidates:
                best_homepage = choose_best_candidate(source_key, homepage_candidates)
                print(
                    f"SELECTED {source_name} HOMEPAGE: score={best_homepage.score:.1f} "
                    f"origin={best_homepage.origin} title={best_homepage.title}"
                )
                article = enrich_article(build_article_from_candidate(best_homepage))
                cache_article(source_key, article)
                return article

        except Exception as error:
            message = f"homepage -> {error}"
            print(f"{source_name} homepage failed: {error}")
            errors.append(message)

    return fallback_article(source_key, " | ".join(errors))



def _preload_article_text_for_value(value):
    if isinstance(value, (list, tuple)):
        for item in value:
            _preload_article_text_for_value(item)
        return

    url = str(getattr(value, "link", "") or "").strip()

    if url:
        prefetch_article_text_payload(url)

def fetch_news_cards(left_source_key="FOX", right_source_key="CNBC"):
    left_source_key = normalize_source_key(left_source_key)
    right_source_key = normalize_source_key(right_source_key)

    if left_source_key == right_source_key:
        articles = fetch_configured_articles(left_source_key, max_articles=5)

        left_article = articles[0]
        right_articles = articles[1:5]

        _preload_article_text_for_value(left_article)
        _preload_article_text_for_value(right_articles)

        return left_article, right_articles

    # Fetch left and right in parallel so a slow optional source does not block the
    # other article card.
    with ThreadPoolExecutor(max_workers=2) as executor:
        left_future = executor.submit(fetch_configured_article, left_source_key)
        right_future = executor.submit(fetch_configured_article, right_source_key)

        left_article = left_future.result()
        right_article = right_future.result()

    _preload_article_text_for_value(left_article)
    _preload_article_text_for_value(right_article)

    return left_article, right_article


def debug_all_news_sources():
    print("\n================ NEWS SOURCE DEBUG ================")
    for source_key in NEWS_SOURCES.keys():
        print(f"\n\n######## DEBUGGING {get_news_source_display(source_key)} ########")
        article = fetch_configured_article(source_key)
        expected = EXPECTED_HEADLINES.get(source_key, "")
        similarity = SequenceMatcher(None, normalize_text(article.title), normalize_text(expected)).ratio()
        print(f"EXPECTED: {expected}")
        print(f"SELECTED: {article.title}")
        print(f"SIMILARITY: {similarity:.2f}")
        print(f"LINK: {article.link}")


if __name__ == "__main__":
    debug_all_news_sources()


def fetch_cnbc_rendered_largest_text_lead_article(source_key="CNBC"):
    """
    Select CNBC's true visible homepage lead from the largest rendered
    editorial headline element, not from a pre-filtered list of links.
    """
    from services.newsmax_chrome import (
        _close_page,
        _create_page,
        _eval,
        _navigate,
    )

    target_id = ""
    ws_url = ""

    try:
        target_id, ws_url = _create_page()
        _navigate(ws_url, CNBC_HOMEPAGE)

        payload = _eval(
            ws_url,
            r"""
(() => {
    const clean = value => String(value || "")
        .replace(/\s+/g, " ")
        .trim();

    const isVisible = node => {
        const style = window.getComputedStyle(node);
        const rect = node.getBoundingClientRect();

        return (
            style.display !== "none" &&
            style.visibility !== "hidden" &&
            Number(style.opacity || 1) > 0 &&
            rect.width >= 100 &&
            rect.height >= 16
        );
    };

    const isEditorialCnbcUrl = href => {
        const value = String(href || "").toLowerCase();

        if (
            !/^https:\/\/www\.cnbc\.com\/20\d{2}\/\d{2}\/\d{2}\/.+\.html$/i.test(
                String(href || "")
            )
        ) {
            return false;
        }

        const blockedPaths = [
            "/pro/",
            "/video/",
            "/watch/",
            "stock-market-today-live-updates"
        ];

        return !blockedPaths.some(bit => value.includes(bit));
    };

    const blockedTitleBits = [
        "watch live",
        "subscribe",
        "newsletter",
        "advertisement",
        "cnbc pro",
        "investing club",
        "sign in",
        "stock market today",
        "live updates"
    ];

    const headlineSelector = [
        "h1",
        "h2",
        "h3",
        "h4",
        "[role='heading']",
        "[class*='headline' i]",
        "[class*='headLine' i]",
        "[class*='title' i]"
    ].join(",");

    const candidates = [];
    const seen = new Set();

    for (const headlineNode of document.querySelectorAll(headlineSelector)) {
        if (!isVisible(headlineNode)) {
            continue;
        }

        const title = clean(
            headlineNode.innerText ||
            headlineNode.textContent ||
            ""
        );

        const titleLower = title.toLowerCase();

        if (
            title.length < 20 ||
            blockedTitleBits.some(bit => titleLower.includes(bit))
        ) {
            continue;
        }

        let link = headlineNode.closest("a[href]");

        if (!link) {
            const card = headlineNode.closest(
                "article, [class*='card' i], [class*='content' i], [class*='story' i]"
            );

            if (card) {
                link = card.querySelector("a[href]");
            }
        }

        const href = String(link?.href || "").trim();

        if (!isEditorialCnbcUrl(href)) {
            continue;
        }

        const rect = headlineNode.getBoundingClientRect();
        const style = window.getComputedStyle(headlineNode);
        const fontSize = parseFloat(style.fontSize) || 0;
        const fontWeight = parseInt(style.fontWeight, 10) || 0;
        const area = Math.round(rect.width * rect.height);

        const image = (
            link?.querySelector("img") ||
            headlineNode.closest("article, [class*='card' i]")?.querySelector("img")
        );

        const imageUrl = image
            ? String(image.currentSrc || image.src || "")
            : "";

        const key = `${title}|${href}`;
        if (seen.has(key)) {
            continue;
        }
        seen.add(key);

        candidates.push({
            title,
            link: href,
            imageUrl,
            fontSize,
            fontWeight,
            area,
            top: Math.round(rect.top),
            left: Math.round(rect.left),
            tag: headlineNode.tagName,
            className: String(headlineNode.className || "").slice(0, 180)
        });
    }

    candidates.sort((a, b) => (
        b.fontSize - a.fontSize ||
        b.area - a.area ||
        b.fontWeight - a.fontWeight ||
        a.top - b.top ||
        a.left - b.left
    ));

    return {
        count: candidates.length,
        selected: candidates[0] || null,
        topCandidates: candidates.slice(0, 20)
    };
})()
""",
            timeout=25,
        )

        if not isinstance(payload, dict):
            raise RuntimeError("Chrome did not return CNBC homepage data")

        print("\n===== CNBC RENDERED HEADLINE CANDIDATES =====")
        for index, candidate in enumerate(
            payload.get("topCandidates", []) or [],
            start=1,
        ):
            print(
                f"{index}. font={candidate.get('fontSize')}px "
                f"area={candidate.get('area')} "
                f"top={candidate.get('top')} "
                f"tag={candidate.get('tag')} "
                f"title={candidate.get('title')}"
            )
            print(f"   link={candidate.get('link')}")

        selected = payload.get("selected") or {}
        title = clean_text(selected.get("title", ""))
        link = str(selected.get("link", "") or "").strip()
        image_url = str(selected.get("imageUrl", "") or "").strip()

        if not title or not link:
            raise RuntimeError(
                "No usable CNBC rendered homepage headline found. "
                f"Candidates seen: {payload.get('count', 0)}"
            )

        article = NewsArticle(
            title=title,
            source=NEWS_SOURCES[source_key]["source_name"],
            image_url=image_url,
            link=link,
        )

        print(
            "CNBC TRUE LARGEST-TEXT LEAD: "
            f'"{article.title}" '
            f'(font={selected.get("fontSize", 0)}px, '
            f'area={selected.get("area", 0)})'
        )
        print(f"CNBC TRUE LEAD LINK: {article.link}")

        return article

    finally:
        if target_id:
            _close_page(target_id)

def extract_cnbc_candidates_from_embedded_json(page_html, base_url):
    import json
    import re
    import urllib.parse

    candidates = []

    def _clean_title(value):
        try:
            return clean_text(value or "")
        except Exception:
            return str(value or "").replace("\n", " ").strip()

    def _make_candidate(title, url, image_url, origin, position):
        title = _clean_title(title)
        url = urllib.parse.urljoin(base_url, url or "")

        if not title or not url:
            return None

        candidate_class = (
            globals().get("NewsCandidate")
            or globals().get("HeadlineCandidate")
            or globals().get("ArticleCandidate")
            or globals().get("Candidate")
        )

        if candidate_class:
            attempts = [
                dict(
                    title=title,
                    link=url,
                    image_url=image_url or "",
                    source_name="CNBC",
                    origin=origin,
                    position=position,
                    score=0.0,
                ),
                dict(
                    title=title,
                    link=url,
                    image_url=image_url or "",
                    source="CNBC",
                    origin=origin,
                    position=position,
                    score=0.0,
                ),
                dict(
                    title=title,
                    url=url,
                    image_url=image_url or "",
                    source_name="CNBC",
                    origin=origin,
                    position=position,
                    score=0.0,
                ),
                dict(title, url, image_url or "", "CNBC", origin, position, 0.0),
                dict(title, url, image_url or "", origin, position, 0.0),
            ]

            for kwargs in attempts[:3]:
                try:
                    return candidate_class(**kwargs)
                except Exception:
                    pass

            for args in attempts[3:]:
                try:
                    return candidate_class(*args)
                except Exception:
                    pass

        return {
            "title": title,
            "link": url,
            "image_url": image_url or "",
            "source_name": "CNBC",
            "origin": origin,
            "position": position,
            "score": 0.0,
        }

    def _walk(obj):
        if isinstance(obj, dict):
            yield obj
            for value in obj.values():
                yield from _walk(value)
        elif isinstance(obj, list):
            for item in obj:
                yield from _walk(item)

    def _extract_balanced_object(source, start_index):
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

    marker = "window.__s_data="
    marker_index = page_html.find(marker)
    if marker_index < 0:
        return candidates

    raw_json = _extract_balanced_object(page_html, marker_index + len(marker))
    if not raw_json:
        return candidates

    try:
        data = json.loads(raw_json)
    except Exception:
        return candidates

    layouts = (
        data.get("page", {})
            .get("page", {})
            .get("layout", [])
    )

    skipped_module_names = {
        "marketsBanner",
        "marketsModule",
        "quickLinks",
        "legacyPlayerContainer",
        "latestNews",
        "watchLiveRightRail",
        "adBoxRail",
        "adBoxInline",
        "portfolioBannerAd",
        "videoBreakerFeatured",
        "videoBreaker",
        "liveTV",
    }

    skipped_section_bits = [
        "/markets/",
        "/investing/",
        "/pro/",
        "cnbc-pro",
        "chart investing pro",
        "options investing pro",
        "analyst calls",
        "playbooks",
    ]

    position = 0

    for layout in layouts:
        for column in layout.get("columns", []) or []:
            for module in column.get("modules", []) or []:
                module_name = module.get("name", "")

                if module_name in skipped_module_names:
                    continue

                module_data = module.get("data", {})

                for node in _walk(module_data):
                    url = node.get("url") or node.get("liveURL") or node.get("href")
                    title = (
                        node.get("headline")
                        or node.get("title")
                        or node.get("shorterHeadline")
                        or node.get("linkHeadline")
                    )

                    if not title or not url:
                        continue

                    url = urllib.parse.urljoin(base_url, url)

                    if "cnbc.com/202" not in url or not url.endswith(".html"):
                        continue

                    section = node.get("section") or {}
                    section_text = " ".join([
                        str(section.get("url", "")),
                        str(section.get("liveURL", "")),
                        str(section.get("title", "")),
                        str(node.get("type", "")),
                        str(node.get("brand", "")),
                    ]).lower()

                    if node.get("premium") is True:
                        continue

                    if any(bit in url.lower() or bit in section_text for bit in skipped_section_bits):
                        continue

                    image_url = ""
                    promo_image = node.get("promoImage")
                    if isinstance(promo_image, dict):
                        image_url = promo_image.get("url", "") or ""

                    position += 1
                    candidate = _make_candidate(
                        title=title,
                        url=url,
                        image_url=image_url,
                        origin=f"homepage_cnbc_sdata:{module_name}",
                        position=position,
                    )

                    if candidate:
                        candidates.append(candidate)

    if candidates:
        return dedupe_candidates(candidates) if "dedupe_candidates" in globals() else candidates

    return candidates


# --- CNBC final homepage/live-story resolver ---
def fetch_cnbc_homepage_lead_article(source_key="CNBC"):
    import json
    import re
    import ssl
    import urllib.request
    from html import unescape

    config = NEWS_SOURCES[source_key]
    homepage_url = config.get("homepage_url") or config.get("homepage") or "https://www.cnbc.com/"

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/125.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }

    def _fetch_url(url):
        try:
            return fetch_url_text(url, timeout=20)
        except Exception:
            req = urllib.request.Request(url, headers=headers)
            ctx = ssl._create_unverified_context()
            with urllib.request.urlopen(req, timeout=20, context=ctx) as resp:
                return resp.read().decode("utf-8", errors="replace")

    def _clean(value):
        value = unescape(str(value or ""))
        try:
            value = value.encode("utf-8").decode("unicode_escape", errors="ignore")
        except Exception:
            pass
        value = re.sub(r"<[^>]+>", " ", value)
        value = re.sub(r"\s+", " ", value)
        try:
            return clean_text(value)
        except Exception:
            return value.strip()

    def _extract_balanced_object(source, start_index):
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

    def _load_s_data(html):
        marker = "window.__s_data="
        marker_index = html.find(marker)

        if marker_index < 0:
            raise RuntimeError("CNBC window.__s_data not found")

        raw_json = _extract_balanced_object(html, marker_index + len(marker))

        if not raw_json:
            raise RuntimeError("Could not extract CNBC window.__s_data JSON")

        return json.loads(raw_json)

    def _walk(obj):
        if isinstance(obj, dict):
            yield obj
            for value in obj.values():
                yield from _walk(value)
        elif isinstance(obj, list):
            for item in obj:
                yield from _walk(item)

    def _best_title(node):
        return _clean(
            node.get("headline")
            or node.get("title")
            or node.get("shorterHeadline")
            or node.get("linkHeadline")
            or node.get("promoTitle")
            or node.get("name")
            or node.get("text")
            or ""
        )

    def _best_url(node):
        url = node.get("url") or node.get("href") or node.get("liveURL") or ""
        url = str(url or "")

        if url.startswith("/"):
            url = "https://www.cnbc.com" + url

        return url.replace("\\/", "/")

    def _is_article_url(url):
        return bool(re.search(r"https://www\.cnbc\.com/20\d{2}/\d{2}/\d{2}/.+\.html$", url))

    def _node_type_text(node):
        return " ".join(
            _clean(node.get(k, ""))
            for k in ["__typename", "type", "contentType", "subType", "moduleName"]
        ).lower()

    def _should_skip_homepage_candidate(module_name, node, title, url):
        module_l = (module_name or "").lower()
        url_l = (url or "").lower()
        title_l = (title or "").lower()

        section = node.get("section") or {}
        section_text = " ".join([
            str(section.get("url", "")),
            str(section.get("liveURL", "")),
            str(section.get("title", "")),
            str(node.get("type", "")),
            str(node.get("brand", "")),
            str(node.get("__typename", "")),
        ]).lower()

        if not title or len(title) < 20:
            return True

        skipped_modules = {
            "marketsbanner",
            "marketsmodule",
            "quicklinks",
            "latestnews",
            "watchliverightrail",
            "adboxrail",
            "adboxinline",
            "portfoliobannerad",
            "legacyplayercontainer",
            "videobreakerfeatured",
            "videobreaker",
            "livetv",
            "watchlive",
            "newsletter",
        }

        if module_l in skipped_modules:
            return True

        if "stock-market-today-live-updates" in url_l:
            return True

        if node.get("premium") is True:
            return True

        if "/pro/" in url_l or "cnbc-pro" in section_text:
            return True

        if "investing club" in section_text:
            return True

        if title_l.startswith("pro:"):
            return True

        return False

    def _select_homepage_featured_story(data):
        layouts = (
            data.get("page", {})
            .get("page", {})
            .get("layout", [])
        )

        seen = set()

        for layout in layouts:
            for column in layout.get("columns", []) or []:
                for module in column.get("modules", []) or []:
                    module_name = module.get("name", "")
                    module_data = module.get("data", {})

                    for node in _walk(module_data):
                        url = _best_url(node)
                        title = _best_title(node)

                        if not _is_article_url(url):
                            continue

                        key = (url, title)
                        if key in seen:
                            continue

                        seen.add(key)

                        if _should_skip_homepage_candidate(module_name, node, title, url):
                            continue

                        return {
                            "title": title,
                            "url": url,
                            "type": str(node.get("type", "") or node.get("__typename", "")),
                            "module": module_name,
                            "image_url": (
                                node.get("promoImage", {}).get("url", "")
                                if isinstance(node.get("promoImage"), dict)
                                else ""
                            ),
                        }

        raise RuntimeError("No usable CNBC homepage featured story found")

    def _extract_live_update_headline(article_html):
        objects = []

        for marker in ["window.__s_data=", "__NEXT_DATA__"]:
            marker_index = article_html.find(marker)
            if marker_index >= 0:
                raw = _extract_balanced_object(article_html, marker_index + len(marker))
                if raw:
                    try:
                        objects.append(json.loads(raw))
                    except Exception:
                        pass

        for match in re.finditer(
            r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
            article_html,
            flags=re.S | re.I,
        ):
            try:
                objects.append(json.loads(match.group(1).strip()))
            except Exception:
                pass

        candidates = []
        seen = set()

        for root in objects:
            for node in _walk(root):
                if not isinstance(node, dict):
                    continue

                title = _best_title(node)
                if not title or len(title) < 20:
                    continue

                title_l = title.lower()
                type_l = _node_type_text(node)

                bad_bits = [
                    "cnbc",
                    "subscribe",
                    "newsletter",
                    "watch:",
                    "squawk",
                    "what to watch ahead",
                    "fed meeting live updates",
                    "top news and analysis",
                    "stock market today",
                    "legacyplayercontainer",
                    "adbox",
                ]

                if any(bit in title_l for bit in bad_bits):
                    continue

                key = (title, type_l)
                if key in seen:
                    continue

                seen.add(key)

                live_weight = 0
                if any(good in type_l for good in ["live", "update", "blog"]):
                    live_weight += 100

                candidates.append((live_weight, title))

        if not candidates:
            return ""

        candidates.sort(key=lambda item: item[0], reverse=True)
        return candidates[0][1]

    homepage_html = _fetch_url(homepage_url)
    homepage_data = _load_s_data(homepage_html)
    homepage_story = _select_homepage_featured_story(homepage_data)

    final_title = homepage_story["title"]
    final_url = homepage_story["url"]
    final_image = homepage_story.get("image_url", "")

    if homepage_story["type"].lower() == "live_story" or "live" in final_url.lower():
        try:
            live_html = _fetch_url(final_url)
            live_title = _extract_live_update_headline(live_html)
            if live_title:
                final_title = live_title
        except Exception as error:
            print(f"CNBC live story page headline fallback failed: {error}")

    class SimpleCandidate:
        pass

    candidate = SimpleCandidate()
    candidate.title = final_title
    candidate.link = final_url
    candidate.image_url = final_image
    candidate.source_name = "CNBC"
    candidate.source = "CNBC"
    candidate.origin = "cnbc_featured_homepage_live_story"
    candidate.position = 1
    candidate.score = 999999.0

    article = enrich_article(build_article_from_candidate(candidate))
    cache_article(source_key, article)

    print(f'SELECTED CNBC FINAL: "{final_title}"')
    return article


# --- CNN homepage lead resolver ---
def fetch_cnn_homepage_lead_article(source_key="CNN"):
    import re
    import ssl
    import urllib.request
    from html import unescape
    from html.parser import HTMLParser
    from urllib.parse import urljoin

    config = NEWS_SOURCES[source_key]
    homepage_url = config.get("homepage_url") or config.get("homepage") or "https://www.cnn.com/"

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/125.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }

    def _fetch_url(url):
        try:
            return fetch_url_text(url, timeout=20)
        except Exception:
            req = urllib.request.Request(url, headers=headers)
            ctx = ssl._create_unverified_context()
            with urllib.request.urlopen(req, timeout=20, context=ctx) as resp:
                return resp.read().decode("utf-8", errors="replace")

    def _clean(value):
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

        try:
            return clean_text(value)
        except Exception:
            return value

    class _CNNAnchorParser(HTMLParser):
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
                self.current["text"] = _clean(raw_text)
                self.current["aria"] = _clean(self.current["aria"])
                self.links.append(self.current)
                self.current = None

    def _is_cnn_article_url(url):
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

    def _should_skip_title(title, url, raw_text="", meta_text=""):
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
            "read the whole",
        ]

        if any(bit in title_l for bit in bad_title_bits):
            return True, "bad title/caption/UI pattern"

        credit_patterns = [
            r"^[A-Z][A-Za-z .'-]+/[A-Z]{2,}$",
            r"^[A-Z][A-Za-z .'-]+/(AP|Reuters|Getty Images|AFP|Bloomberg)(/Getty Images)?$",
            r"^[A-Z][A-Za-z .'-]+\s*/\s*(AP|Reuters|Getty Images|AFP|Bloomberg)",
        ]

        for pattern in credit_patterns:
            if re.search(pattern, title, flags=re.I):
                return True, "image credit/caption text"

        if any(bit in raw_l for bit in ["getty images", "afp/getty", "ap photo", "reuters", "bloomberg/getty"]):
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

    def _score_candidate(candidate):
        score = 0
        raw_l = candidate["raw_text"].lower()
        title_l = candidate["title"].lower()
        meta_l = candidate["meta"].lower()

        # Structural homepage lead-package signals.
        if "show all" in raw_l:
            score += 1000
        if "breaking news" in raw_l:
            score += 600
        if "container__headline" in meta_l or "headline" in meta_l:
            score += 200

        if 25 <= len(candidate["title"]) <= 95:
            score += 100

        if title_l.startswith(("trump ", "video ", "analysis ", "cnn poll ")):
            score -= 50

        score -= candidate["position"] * 0.01
        return score

    def _find_homepage_image_for_candidate(html, selected):
        def _norm(value):
            value = str(value or "")
            value = value.replace("\\/", "/")
            value = value.replace("&amp;", "&")
            return value

        def _find_all_positions(needle):
            positions = []
            if not needle:
                return positions

            pos = 0
            while True:
                idx = html.find(needle, pos)
                if idx < 0:
                    break
                positions.append(idx)
                pos = idx + len(needle)

            return positions

        url = selected.get("url", "")
        title = selected.get("title", "")

        url_needles = [
            url,
            url.replace("https://www.cnn.com", ""),
            url.replace("https://cnn.com", ""),
            url.replace("/", "\\/"),
            url.replace("https://www.cnn.com", "").replace("/", "\\/"),
        ]

        title_needles = [
            title,
            f"{title} Show all",
        ]

        title_positions = []
        for needle in title_needles:
            title_positions.extend(_find_all_positions(needle))

        url_positions = []
        for needle in url_needles:
            url_positions.extend(_find_all_positions(needle))

        anchors = sorted(set(title_positions + url_positions))
        if not anchors:
            return ""

        # Use the first real occurrence of the selected front-page card.
        anchor_pos = anchors[0]

        # Tight front-page package window. Start slightly before the headline to keep same-card picture tags,
        # but score images after the headline/URL much higher so previous-card images lose.
        window_start = max(0, anchor_pos - 1200)
        window_end = min(len(html), anchor_pos + 14000)
        block = html[window_start:window_end]

        image_patterns = [
            r'https?:\\?/\\?/media\.cnn\.com/api/v1/images/stellar/prod/[^"\'<>\s,]+',
            r'https?:\\?/\\?/media\.cnn\.com/[^"\'<>\s,]+\.(?:jpg|jpeg|png|webp)(?:\?[^"\'<>\s,]+)?',
            r'https?:\\?/\\?/cdn\.cnn\.com/[^"\'<>\s,]+\.(?:jpg|jpeg|png|webp)(?:\?[^"\'<>\s,]+)?',
            r'"uri"\s*:\s*"([^"]+)"',
            r'"url"\s*:\s*"([^"]+\.(?:jpg|jpeg|png|webp)[^"]*)"',
        ]

        images = []

        for pattern in image_patterns:
            for match in re.finditer(pattern, block, flags=re.I):
                raw = match.group(1) if match.groups() else match.group(0)
                image_url = _norm(raw)
                absolute_pos = window_start + match.start()

                if image_url.startswith("//"):
                    image_url = "https:" + image_url

                if image_url.startswith("/"):
                    image_url = "https://www.cnn.com" + image_url

                low = image_url.lower()

                if not any(host in low for host in ["media.cnn.com", "cdn.cnn.com"]):
                    continue

                if any(bad in low for bad in [
                    "logo",
                    "favicon",
                    "icon",
                    "sprite",
                    "placeholder",
                    "avatar",
                    "loader",
                ]):
                    continue

                images.append({
                    "url": image_url,
                    "pos": absolute_pos,
                })

        deduped = []
        seen = set()
        for item in images:
            if item["url"] in seen:
                continue
            seen.add(item["url"])
            deduped.append(item)

        if not deduped:
            return ""

        def _score_image(item):
            image_url = item["url"]
            low = image_url.lower()
            pos = item["pos"]

            score = 0

            # Main fix: previous story images are before the selected headline/url.
            # Same-card CNN lead image appears after the selected lead link/title block.
            if pos >= anchor_pos:
                score += 100000
            else:
                score -= 50000

            # Prefer closer images after the selected card anchor.
            score -= abs(pos - anchor_pos) * 0.01

            # Prefer canonical/original CNN image variant over resized crop URLs.
            if "c=original" in low:
                score += 5000
            elif "16x9" in low:
                score += 1000

            if "media.cnn.com/api/v1/images/stellar/prod" in low:
                score += 500

            return score

        deduped.sort(key=_score_image, reverse=True)
        return deduped[0]["url"]


    def _force_article_homepage_image(article, image_url):
        if not image_url:
            return article

        if isinstance(article, dict):
            article["image_url"] = image_url
            article["image"] = image_url
            article["thumbnail_url"] = image_url
            return article

        for attr in ("image_url", "image", "thumbnail_url"):
            try:
                setattr(article, attr, image_url)
            except Exception:
                pass

        return article


    def _anchor_candidates(html):
        parser = _CNNAnchorParser()
        parser.feed(html)

        candidates = []
        seen = set()
        position = 0

        for link in parser.links:
            url = urljoin(homepage_url, link["href"]).split("?")[0].split("#")[0]

            if not _is_cnn_article_url(url):
                continue

            raw_text = link.get("raw_text", "")
            title = _clean(link["aria"] or link["text"])

            key = (url, title)
            if key in seen:
                continue
            seen.add(key)

            position += 1

            meta = " ".join([link.get("class", ""), link.get("data", "")])
            skip, reason = _should_skip_title(title, url, raw_text, meta)

            candidate = {
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
                candidate["score"] = _score_candidate(candidate)

            candidates.append(candidate)

        return candidates

    html = _fetch_url(homepage_url)
    candidates = _anchor_candidates(html)
    keepers = [candidate for candidate in candidates if not candidate["skip"]]

    if not keepers:
        raise RuntimeError("No usable CNN homepage candidate found")

    selected = max(keepers, key=lambda candidate: candidate["score"])
    final_image = _find_homepage_image_for_candidate(html, selected)

    class SimpleCandidate:
        pass

    candidate = SimpleCandidate()
    candidate.title = selected["title"]
    candidate.link = selected["url"]
    candidate.image_url = final_image
    candidate.source_name = "CNN"
    candidate.source = "CNN"
    candidate.origin = "cnn_homepage_anchor_lead"
    candidate.position = selected["position"]
    candidate.score = selected["score"]

    article = enrich_article(build_article_from_candidate(candidate))
    article = _force_article_homepage_image(article, final_image)
    cache_article(source_key, article)

    print(f'SELECTED CNN FINAL: "{selected["title"]}"')
    print(f'SELECTED CNN HOMEPAGE IMAGE: "{final_image}"')
    return article



# ============================================================
# Source-specific homepage lead resolvers
# Added so FoxNews.com and CNN.com do NOT share the same rules.
# Fox keeps the existing homepage-anchor logic.
# CNN gets CNN-specific logic that allows live-news lead stories.
# ============================================================

try:
    _FOX_EXISTING_HOMEPAGE_LEAD_RESOLVER = fetch_cnn_homepage_lead_article
except NameError:
    _FOX_EXISTING_HOMEPAGE_LEAD_RESOLVER = None


def fetch_fox_homepage_lead_article(source_key="FOX"):
    """
    Select Fox's visible homepage lead by rendered headline prominence.

    Fox JSON-LD ordering is not reliable for the actual visual lead card.
    """
    import time
    from services.newsmax_chrome import _close_page, _create_page, _eval, _navigate

    homepage_url = (
        NEWS_SOURCES[source_key].get("homepage_url")
        or NEWS_SOURCES[source_key].get("homepage")
        or "https://www.foxnews.com/"
    )

    target_id = ""
    ws_url = ""
    last_error = None

    try:
        for attempt in range(1, 4):
            try:
                target_id, ws_url = _create_page()
                _navigate(ws_url, homepage_url)

                payload = _eval(
                    ws_url,
                    r"""
(() => {
    const clean = value => String(value || "")
        .replace(/\s+/g, " ")
        .trim();

    const visible = element => {
        const style = getComputedStyle(element);
        const rect = element.getBoundingClientRect();

        return (
            style.display !== "none" &&
            style.visibility !== "hidden" &&
            Number(style.opacity || 1) > 0 &&
            rect.width > 20 &&
            rect.height > 10
        );
    };

    const validFoxArticle = href => {
        try {
            const url = new URL(href);
            const host = url.hostname.toLowerCase();
            const path = url.pathname.toLowerCase();

            if (!host.endsWith("foxnews.com")) return false;

            const blocked = [
                "/video/", "/watch/", "/shows/", "/person/", "/category/",
                "/radio/", "/podcasts/", "/weather/", "/newsletter",
                "/deals", "/fox-news-shop", "/login", "/search", "/about"
            ];

            if (blocked.some(bit => path.includes(bit))) return false;

            return path.split("/").filter(Boolean).length >= 2;
        } catch {
            return false;
        }
    };

    const blockedTitles = [
        "subscribe", "newsletter", "sign up", "watch live",
        "live tv", "weather", "advertisement", "sponsored",
        "privacy policy", "terms of use"
    ];

    const candidates = [];
    const seen = new Set();

    for (const link of document.querySelectorAll("a[href]")) {
        const href = String(link.href || "").trim();

        if (!validFoxArticle(href) || !visible(link)) continue;

        const nodes = [
            link,
            ...Array.from(
                link.querySelectorAll(
                    "h1, h2, h3, h4, h5, h6, [class*='headline'], [class*='title']"
                )
            )
        ].filter(visible);

        let best = null;

        for (const node of nodes) {
            const title = clean(node.innerText || node.textContent);
            const lower = title.toLowerCase();

            if (
                title.length < 20 ||
                blockedTitles.some(bit => lower.includes(bit))
            ) continue;

            const style = getComputedStyle(node);
            const rect = node.getBoundingClientRect();

            const card =
                link.closest("article") ||
                link.closest("li") ||
                link.closest("section") ||
                link;

            const imageNodes = [
                ...link.querySelectorAll("img"),
                ...card.querySelectorAll("img")
            ];

            const normalizedTitle = title.toLowerCase();

            const imageNode =
                imageNodes.find(img => {
                    const alt = String(img.alt || "")
                        .replace(/\s+/g, " ")
                        .trim()
                        .toLowerCase();

                    return alt.includes(normalizedTitle);
                }) ||
                imageNodes.find(img => {
                    const imageRect = img.getBoundingClientRect();
                    return imageRect.width > 100 && imageRect.height > 80;
                }) ||
                null;

            const image = imageNode
                ? String(
                    imageNode.currentSrc ||
                    imageNode.src ||
                    imageNode.getAttribute("data-src") ||
                    imageNode.getAttribute("data-lazy-src") ||
                    ""
                ).trim()
                : "";

            const item = {
                title,
                link: href,
                image,
                fontSize: parseFloat(style.fontSize || "0") || 0,
                fontWeight: parseInt(style.fontWeight || "400", 10) || 400,
                top: Math.round(rect.top),
                left: Math.round(rect.left)
            };

            if (
                !best ||
                item.fontSize > best.fontSize ||
                (
                    item.fontSize === best.fontSize &&
                    item.fontWeight > best.fontWeight
                )
            ) {
                best = item;
            }
        }

        if (!best) continue;

        const key = `${best.title.toLowerCase()}|${best.link.toLowerCase()}`;

        if (seen.has(key)) continue;

        seen.add(key);
        candidates.push(best);
    }

    candidates.sort((a, b) =>
        b.fontSize - a.fontSize ||
        b.fontWeight - a.fontWeight ||
        a.top - b.top ||
        a.left - b.left
    );

    return {
        selected: candidates[0] || null
    };
})()
""",
                    timeout=25,
                )

                selected = (payload or {}).get("selected") or {}
                title = clean_text(selected.get("title", ""))
                link = str(selected.get("link", "") or "").strip()
                image = str(selected.get("image", "") or "").strip()

                if not title or not link:
                    raise RuntimeError("No rendered Fox homepage lead article found")

                print(
                    "SELECTED FOX RENDERED HOMEPAGE LEAD: "
                    f"{title} | {selected.get('fontSize', 0)}px"
                )
                print(f"FOX RENDERED LEAD LINK: {link}")
                print(f"FOX RENDERED LEAD IMAGE: {image}")

                return {
                    "source": source_key,
                    "title": title,
                    "link": link,
                    "url": link,
                    "summary": "",
                    "image": image,
                    "published": "",
                }

            except Exception as error:
                last_error = error
                print(f"Fox rendered lead attempt {attempt} failed: {error}")

                if target_id:
                    _close_page(target_id)
                    target_id = ""
                    ws_url = ""

                time.sleep(2)

        raise RuntimeError(f"Fox rendered homepage lead failed: {last_error}")

    finally:
        if target_id:
            _close_page(target_id)

def fetch_cnn_homepage_lead_article(source_key="CNN"):
    """
    CNN.com resolver.

    CNN often places the lead headline on /live-news/ URLs, so CNN needs
    separate rules from Fox. In particular, do NOT reject /live-news/.
    """
    import re
    import ssl
    import urllib.request
    from html import unescape
    from html.parser import HTMLParser
    from urllib.parse import urljoin

    config = NEWS_SOURCES[source_key]
    homepage_url = config.get("homepage_url") or config.get("homepage") or "https://www.cnn.com/"

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/125.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }

    def _fetch_url(url):
        try:
            return fetch_url_text(url, timeout=20)
        except Exception:
            req = urllib.request.Request(url, headers=headers)
            ctx = ssl._create_unverified_context()
            with urllib.request.urlopen(req, timeout=20, context=ctx) as resp:
                return resp.read().decode("utf-8", errors="replace")

    def _clean(value):
        value = unescape(str(value or ""))

        replacements = {
            "Ã¢Â€Â™": "'",
            "Ã¢Â€Â˜": "'",
            "Ã¢Â€Âœ": '"',
            "Ã¢Â€Â�": '"',
            "Ã¢Â€Â�": '"',
            "Ã¢Â�Â�": '"',
            "Ã¢Â�Â¢": "•",
            "Ã¢Â€Â¢": "•",
        }

        for bad, good in replacements.items():
            value = value.replace(bad, good)

        value = re.sub(r"<[^>]+>", " ", value)
        value = re.sub(r"\s+", " ", value).strip()

        # CNN-specific UI cleanup.
        value = re.sub(r"\s+Show\s+all\s*$", "", value, flags=re.I).strip()
        value = re.sub(r"^•\s*", "", value).strip()
        value = re.sub(
            r"^Live Updates\s+(?:\d+\s+min(?:ute)?s? ago|a min ago)\s+",
            "",
            value,
            flags=re.I,
        ).strip()
        value = re.sub(
            r"^(Breaking News|Analysis|Video|CNN Exclusive|For Subscribers)\s+",
            "",
            value,
            flags=re.I,
        ).strip()

        try:
            return clean_text(value)
        except Exception:
            return value

    class _CNNAnchorParser(HTMLParser):
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
                    "data": " ".join(
                        f"{k}={v}" for k, v in attrs.items() if k.startswith("data-")
                    ),
                }

        def handle_data(self, data):
            if self.current is not None:
                self.current["text_parts"].append(data)

        def handle_endtag(self, tag):
            if tag == "a" and self.current is not None:
                raw_text = " ".join(self.current["text_parts"])
                self.current["raw_text"] = raw_text
                self.current["text"] = _clean(raw_text)
                self.current["aria"] = _clean(self.current["aria"])
                self.links.append(self.current)
                self.current = None

    def _is_cnn_article_url(url):
        low = url.lower()

        if "cnn.com/202" not in low:
            return False

        # CNN difference from Fox:
        # DO NOT block /live-news/ because CNN's main lead is often there.
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
            "/gallery/",
            "/profiles/",
        ]

        return not any(bit in low for bit in bad_bits)

    def _should_skip_title(title, url, raw_text="", meta_text=""):
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
            "read the whole",
        ]

        if any(bit in title_l for bit in bad_title_bits):
            return True, "bad title/caption/UI pattern"

        credit_patterns = [
            r"^[A-Z][A-Za-z .'-]+/[A-Z]{2,}$",
            r"^[A-Z][A-Za-z .'-]+/(AP|Reuters|Getty Images|AFP|Bloomberg)(/Getty Images)?$",
            r"^[A-Z][A-Za-z .'-]+\s*/\s*(AP|Reuters|Getty Images|AFP|Bloomberg)",
        ]

        for pattern in credit_patterns:
            if re.search(pattern, title, flags=re.I):
                return True, "image credit/caption text"

        if any(bit in raw_l for bit in ["getty images", "afp/getty", "ap photo", "reuters", "bloomberg/getty"]):
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

    def _score_candidate(title, url, raw_text="", meta_text="", position=9999):
        title_l = title.lower()
        url_l = url.lower()
        raw_l = raw_text.lower()
        meta_l = meta_text.lower()

        score = 1000.0

        # Earlier homepage anchors are usually more important.
        score += max(0, 600 - position * 10)

        # CNN homepage lead/live-news boost.
        if "/live-news/" in url_l:
            score += 500

        if any(word in title_l for word in ["trump", "iran", "israel", "war", "supreme court", "white house"]):
            score += 120

        if "homepage" in meta_l or "zone" in meta_l or "card" in meta_l:
            score += 75

        if "live updates" in raw_l:
            score -= 80

        if "trending" in raw_l or "latest" in raw_l:
            score -= 120

        return score

    html = _fetch_url(homepage_url)

    # CNN's visual homepage lead is represented by a container_lead-package.
    # Select its title/link before falling back to generic anchor scoring.
    lead_positions = [
        match.start()
        for match in re.finditer(
            r"data-layout=[\"']container_lead-package[\"']",
            html,
            flags=re.IGNORECASE,
        )
    ]

    for lead_position in lead_positions:
        block = html[lead_position:lead_position + 60000]

        title_match = re.search(
            r"<a\s+href=[\"']([^\"']+)[\"'][^>]*"
            r"class=[\"'][^\"']*container__title-url[^\"']*[\"'][^>]*>"
            r'.{0,3000}?<h2[^>]*>(.*?)</h2>',
            block,
            flags=re.IGNORECASE | re.DOTALL,
        )

        if not title_match:
            continue

        lead_url = urljoin(
            homepage_url,
            title_match.group(1),
        ).replace("\\/", "/")

        lead_title = _clean(
            re.sub(r"<[^>]+>", " ", title_match.group(2))
        )

        if not _is_cnn_article_url(lead_url):
            continue

        skip, reason = _should_skip_title(
            lead_title,
            lead_url,
            raw_text=block[:5000],
            meta_text="container_lead-package",
        )

        if skip:
            print(
                "Skipping CNN lead package: "
                f"{lead_title} ({reason})"
            )
            continue

        print(
            "SELECTED CNN LEAD PACKAGE: "
            f"{lead_title}"
        )

        return {
            "source": source_key,
            "title": lead_title,
            "link": lead_url,
            "url": lead_url,
            "summary": "",
            "image": "",
            "published": "",
        }

    parser = _CNNAnchorParser()
    parser.feed(html)

    candidates = []
    seen = set()

    for position, link in enumerate(parser.links, 1):
        href = link.get("href") or ""
        url = urljoin(homepage_url, href).replace("\\/", "/")

        if not _is_cnn_article_url(url):
            continue

        title = link.get("text") or link.get("aria") or ""
        title = _clean(title)

        raw_text = link.get("raw_text", "")
        meta_text = " ".join([
            link.get("class", ""),
            link.get("aria", ""),
            link.get("data", ""),
        ])

        skip, reason = _should_skip_title(title, url, raw_text=raw_text, meta_text=meta_text)

        if skip:
            continue

        key = (title.lower(), url.lower())
        if key in seen:
            continue
        seen.add(key)

        candidates.append({
            "title": title,
            "link": url,
            "score": _score_candidate(
                title,
                url,
                raw_text=raw_text,
                meta_text=meta_text,
                position=position,
            ),
            "position": position,
            "reason": reason,
        })

    if not candidates:
        raise RuntimeError("No usable CNN homepage lead article found")

    selected = sorted(candidates, key=lambda item: item["score"], reverse=True)[0]

    return {
        "source": source_key,
        "title": selected["title"],
        "link": selected["link"],
        "url": selected["link"],
        "summary": "",
        "image": "",
        "published": "",
    }


def fetch_source_specific_homepage_lead_article(source_key):
    """
    Dispatcher for source-specific homepage lead logic.
    Use this where the app asks for homepage lead news.
    """
    key = str(source_key or "").upper()

    if key in {"FOX", "FOXNEWS", "FOX NEWS"}:
        return fetch_fox_homepage_lead_article(source_key)

    if key == "CNN":
        return fetch_cnn_homepage_lead_article(source_key)

    if _FOX_EXISTING_HOMEPAGE_LEAD_RESOLVER is not None:
        return _FOX_EXISTING_HOMEPAGE_LEAD_RESOLVER(source_key)

    raise RuntimeError(f"No homepage lead resolver available for source: {source_key}")



# ============================================================
# CNN rendered homepage resolver
#
# CNN's raw page contains footer "Listen" and podcast links alongside
# editorial cards. Use the rendered page so visible headline typography,
# card placement, and page position determine the lead and top stories.
# ============================================================

_GENERIC_FETCH_RANKED_CANDIDATES = fetch_generic_ranked_candidates


def _cnn_is_english_editorial_candidate(title, url):
    title = clean_text(title)
    url_l = str(url or "").lower()
    title_l = title.lower()

    if len(title) < 20 or len(title.split()) < 4:
        return False

    blocked_url_bits = [
        "/audio/",
        "/podcasts/",
        "/videos/",
        "/video/",
        "/espanol/",
        "/es/",
        "/cnn-underscored/",
        "/style/",
        "/travel/",
        "/weather/",
        "/interactive/",
        "/live-tv/",
        "/listen/",
    ]

    if any(bit in url_l for bit in blocked_url_bits):
        return False

    blocked_title_bits = [
        "chasing life with dr. sanjay gupta",
        "all there is with anderson cooper",
        "the assignment with audie cornish",
        "cnn underscored",
        "listen to",
        "watch live",
        "newsletter",
        "subscribe",
        "sign up",
        "podcast",
        "audio",
        "privacy policy",
        "terms of use",
        "advertisement",
        "sponsored",
    ]

    if any(bit in title_l for bit in blocked_title_bits):
        return False

    # This is intentionally conservative. It catches obviously Spanish
    # homepage cards without rejecting English names or foreign locations.
    spanish_markers = [
        " en español ",
        "terremoto",
        "noticias",
        "última hora",
        "mundo ",
        "venezuela se ",
        " estados unidos ",
    ]

    padded_title = f" {title_l} "

    if any(marker in padded_title for marker in spanish_markers):
        return False

    return True


def fetch_cnn_rendered_homepage_candidates():
    from services.newsmax_chrome import (
        _close_page,
        _create_page,
        _eval,
        _navigate,
    )

    homepage_url = "https://www.cnn.com/"
    target_id = ""
    ws_url = ""

    try:
        target_id, ws_url = _create_page()
        _navigate(ws_url, homepage_url)

        payload = _eval(
            ws_url,
            r"""
(() => {
    const clean = value => String(value || "")
        .replace(/\s+/g, " ")
        .trim();

    const visible = element => {
        if (!element) return false;

        const style = getComputedStyle(element);
        const rect = element.getBoundingClientRect();

        return (
            style.display !== "none" &&
            style.visibility !== "hidden" &&
            Number(style.opacity || 1) > 0 &&
            rect.width > 40 &&
            rect.height > 12 &&
            rect.bottom > 0
        );
    };

    const validCnnArticle = href => {
        try {
            const url = new URL(href);
            const host = url.hostname.toLowerCase();
            const path = url.pathname.toLowerCase();

            if (!(host === "cnn.com" || host.endsWith(".cnn.com"))) {
                return false;
            }

            if (!/^\/202\d\//.test(path)) {
                return false;
            }

            const blocked = [
                "/audio/",
                "/podcasts/",
                "/videos/",
                "/video/",
                "/espanol/",
                "/cnn-underscored/",
                "/style/",
                "/travel/",
                "/interactive/",
                "/live-tv/",
                "/listen/"
            ];

            return !blocked.some(bit => path.includes(bit));
        } catch {
            return false;
        }
    };

    const ignoredContainers = [
        "footer",
        "nav",
        "[role='navigation']",
        "[class*='footer']",
        "[class*='Footer']",
        "[class*='podcast']",
        "[class*='Podcast']",
        "[class*='audio']",
        "[class*='Audio']",
        "[class*='listen']",
        "[class*='Listen']"
    ];

    const blockedText = [
        "chasing life with dr. sanjay gupta",
        "all there is with anderson cooper",
        "the assignment with audie cornish",
        "cnn underscored",
        "newsletter",
        "subscribe",
        "sign up",
        "listen to",
        "watch live",
        "podcast",
        "audio",
        "advertisement",
        "sponsored"
    ];

    const candidates = [];
    const seen = new Set();

    for (const link of document.querySelectorAll("a[href]")) {
        const href = String(link.href || "").trim();

        if (!validCnnArticle(href) || !visible(link)) {
            continue;
        }

        if (ignoredContainers.some(selector => link.closest(selector))) {
            continue;
        }

        const nodes = [
            ...link.querySelectorAll(
                "h1, h2, h3, h4, h5, h6, [class*='headline'], [class*='Headline'], [class*='title'], [class*='Title']"
            ),
            link
        ].filter(visible);

        let bestNode = null;
        let bestTitle = "";
        let bestFontSize = 0;

        for (const node of nodes) {
            const title = clean(node.innerText || node.textContent);
            const lower = title.toLowerCase();

            if (
                title.length < 20 ||
                blockedText.some(bit => lower.includes(bit))
            ) {
                continue;
            }

            const style = getComputedStyle(node);
            const fontSize = Number.parseFloat(style.fontSize || "0") || 0;

            if (fontSize >= bestFontSize) {
                bestFontSize = fontSize;
                bestNode = node;
                bestTitle = title;
            }
        }

        if (!bestNode || !bestTitle) {
            continue;
        }

        const headlineRect = bestNode.getBoundingClientRect();
        const card =
            link.closest("article") ||
            link.closest("section") ||
            link.closest("li") ||
            link.parentElement ||
            link;

        const cardRect = card.getBoundingClientRect();

        const key = `${href}|${bestTitle.toLowerCase()}`;

        if (seen.has(key)) {
            continue;
        }

        seen.add(key);

        const image =
            card.querySelector("img[src]") ||
            link.querySelector("img[src]");

        candidates.push({
            title: bestTitle,
            link: href,
            image_url: image ? String(image.currentSrc || image.src || "") : "",
            font_size: bestFontSize,
            top: Math.max(0, headlineRect.top),
            left: Math.max(0, headlineRect.left),
            card_area: Math.max(0, cardRect.width * cardRect.height),
            class_text: `${link.className || ""} ${bestNode.className || ""}`,
            position: candidates.length + 1
        });
    }

    return candidates;
})()
""",
            timeout=25,
        )

        if not isinstance(payload, list):
            raise RuntimeError("CNN Chrome resolver returned no candidate list")

        candidates = []

        for item in payload:
            if not isinstance(item, dict):
                continue

            title = clean_text(item.get("title", ""))
            link = str(item.get("link", "") or "").strip()
            image_url = str(item.get("image_url", "") or "").strip()

            if not _cnn_is_english_editorial_candidate(title, link):
                continue

            font_size = float(item.get("font_size", 0) or 0)
            top = float(item.get("top", 999999) or 999999)
            card_area = float(item.get("card_area", 0) or 0)

            # Larger rendered headlines are the strongest lead signal.
            # Earlier placement breaks ties. Card area helps favor the main
            # hero package over small rail cards.
            score = (
                font_size * 10000
                - min(top, 6000) * 4
                + min(card_area, 2_000_000) / 250
            )

            candidates.append(
                Candidate(
                    title=title,
                    source="CNN",
                    image_url=image_url,
                    link=link,
                    origin="cnn_rendered_homepage",
                    position=int(item.get("position", 999999) or 999999),
                    score=score,
                )
            )

        candidates = dedupe_candidates(candidates)
        candidates.sort(key=lambda item: item.score, reverse=True)

        if not candidates:
            raise RuntimeError(
                "No usable English editorial CNN homepage candidates found"
            )

        print("\n===== CNN rendered homepage candidates =====")
        for index, candidate in enumerate(candidates[:10], start=1):
            print(
                f"{index}. score={candidate.score:.1f} "
                f"font/title={candidate.title}"
            )
            print(f"   link={candidate.link}")

        return candidates

    finally:
        if target_id:
            _close_page(target_id)


def fetch_cnn_homepage_lead_article(source_key="CNN"):
    candidates = fetch_cnn_rendered_homepage_candidates()
    selected = candidates[0]

    print(f'SELECTED CNN RENDERED LEAD: "{selected.title}"')
    print(f"SELECTED CNN RENDERED LINK: {selected.link}")

    return {
        "source": source_key,
        "title": selected.title,
        "link": selected.link,
        "url": selected.link,
        "summary": "",
        "image": selected.image_url,
        "image_url": selected.image_url,
        "published": "",
    }


def fetch_ranked_candidates(source_key):
    normalized_source = normalize_source_key(source_key)

    if normalized_source != "CNN":
        return _GENERIC_FETCH_RANKED_CANDIDATES(normalized_source)

    candidates = fetch_cnn_rendered_homepage_candidates()

    # The lead card uses the first item. The More Headlines panel already
    # skips index zero, so it receives the next editorial homepage stories.
    return "CNN", "CNN", candidates

# ============================================================
# FINAL CNN RENDERED HOMEPAGE OVERRIDE
# ============================================================


# ============================================================
# FINAL CNN RENDERED HOMEPAGE OVERRIDE
# ============================================================

_GENERIC_FETCH_RANKED_CANDIDATES = fetch_generic_ranked_candidates


def fetch_cnn_rendered_homepage_candidates():
    from services.newsmax_chrome import (
        _close_page,
        _create_page,
        _eval,
        _navigate,
    )

    target_id = ""
    ws_url = ""

    try:
        target_id, ws_url = _create_page()
        _navigate(ws_url, "https://www.cnn.com/")

        raw_candidates = _eval(
            ws_url,
            r"""
(() => {
    const clean = value => String(value || "")
        .replace(/\s+/g, " ")
        .trim();

    const visible = element => {
        if (!element) return false;

        const style = getComputedStyle(element);
        const rect = element.getBoundingClientRect();

        return (
            style.display !== "none" &&
            style.visibility !== "hidden" &&
            Number(style.opacity || 1) > 0 &&
            rect.width > 40 &&
            rect.height > 12 &&
            rect.bottom > 0
        );
    };

    const isCnnArticle = href => {
        try {
            const url = new URL(href);
            const host = url.hostname.toLowerCase();
            const path = url.pathname.toLowerCase();

            if (!(host === "cnn.com" || host.endsWith(".cnn.com"))) {
                return false;
            }

            if (!/^\/202\d\//.test(path)) {
                return false;
            }

            const blockedPaths = [
                "/audio/",
                "/podcasts/",
                "/videos/",
                "/video/",
                "/espanol/",
                "/listen/",
                "/cnn-underscored/",
                "/style/",
                "/travel/",
                "/interactive/"
            ];

            return !blockedPaths.some(bit => path.includes(bit));
        } catch {
            return false;
        }
    };

    const blockedText = [
        "chasing life with dr. sanjay gupta",
        "all there is with anderson cooper",
        "the assignment with audie cornish",
        "podcast",
        "audio",
        "newsletter",
        "subscribe",
        "sign up",
        "listen to",
        "watch live",
        "advertisement",
        "sponsored",
        "en español"
    ];

    const seen = new Set();
    const candidates = [];

    for (const link of document.querySelectorAll("a[href]")) {
        if (!visible(link) || !isCnnArticle(link.href)) {
            continue;
        }

        if (
            link.closest("footer") ||
            link.closest("nav") ||
            link.closest("[role='navigation']") ||
            link.closest("[class*='footer']") ||
            link.closest("[class*='Footer']") ||
            link.closest("[class*='podcast']") ||
            link.closest("[class*='Podcast']") ||
            link.closest("[class*='audio']") ||
            link.closest("[class*='Audio']") ||
            link.closest("[class*='listen']") ||
            link.closest("[class*='Listen']")
        ) {
            continue;
        }

        const headlineNodes = [
            ...link.querySelectorAll(
                "h1, h2, h3, h4, h5, h6, " +
                "[class*='headline'], [class*='Headline'], " +
                "[class*='title'], [class*='Title']"
            ),
            link
        ].filter(visible);

        let best = null;

        for (const node of headlineNodes) {
            const title = clean(node.innerText || node.textContent);
            const titleLower = title.toLowerCase();

            if (
                title.length < 20 ||
                blockedText.some(bit => titleLower.includes(bit))
            ) {
                continue;
            }

            const style = getComputedStyle(node);
            const rect = node.getBoundingClientRect();
            const fontSize = Number.parseFloat(style.fontSize || "0") || 0;
            const fontWeight = Number.parseFloat(style.fontWeight || "0") || 0;

            if (
                !best ||
                fontSize > best.fontSize ||
                (
                    fontSize === best.fontSize &&
                    fontWeight > best.fontWeight
                )
            ) {
                best = {
                    title,
                    fontSize,
                    fontWeight,
                    top: Math.max(0, rect.top),
                    left: Math.max(0, rect.left),
                    className: String(node.className || "")
                };
            }
        }

        if (!best) {
            continue;
        }

        const key = `${link.href}|${best.title.toLowerCase()}`;

        if (seen.has(key)) {
            continue;
        }

        seen.add(key);

        const image =
            link.querySelector("img[src]") ||
            (link.closest("article, section, li") || link.parentElement)
                ?.querySelector?.("img[src]");

        candidates.push({
            title: best.title,
            link: link.href,
            image_url: image
                ? String(image.currentSrc || image.src || "")
                : "",
            font_size: best.fontSize,
            font_weight: best.fontWeight,
            top: best.top,
            left: best.left,
            class_name: best.className
        });
    }

    return candidates;
})()
""",
            timeout=25,
        )

        candidates = []

        for position, item in enumerate(raw_candidates or [], start=1):
            if not isinstance(item, dict):
                continue

            title = clean_text(item.get("title", ""))
            link = str(item.get("link", "") or "").strip()
            image_url = str(item.get("image_url", "") or "").strip()

            if not title or not link:
                continue

            title_lower = title.lower()
            link_lower = link.lower()

            if (
                "en español" in title_lower
                or "terremoto" in title_lower
                or "cnnespanol.cnn.com" in link_lower
            ):
                continue

            font_size = float(item.get("font_size", 0) or 0)
            font_weight = float(item.get("font_weight", 0) or 0)
            top = float(item.get("top", 999999) or 999999)

            candidates.append(
                Candidate(
                    title=title,
                    source="CNN",
                    image_url=image_url,
                    link=link,
                    origin="cnn_rendered_font_rank",
                    position=position,
                    score=(
                        font_size * 100000
                        + font_weight * 10
                        - min(top, 20000)
                    ),
                )
            )

        candidates = dedupe_candidates(candidates)

        candidates.sort(
            key=lambda candidate: (
                -candidate.score,
                candidate.position,
            )
        )

        if not candidates:
            raise RuntimeError(
                "No usable rendered English CNN homepage candidates found."
            )

        print("\n================ CNN FINAL RENDERED RANKING ================")

        for index, candidate in enumerate(candidates[:6], start=1):
            label = "LEAD" if index == 1 else f"TOP STORY {index - 1}"

            print(f"{label}: {candidate.title}")
            print(f"  {candidate.link}")

        return candidates

    finally:
        if target_id:
            _close_page(target_id)


def fetch_cnn_homepage_lead_article(source_key="CNN"):
    candidates = fetch_cnn_rendered_homepage_candidates()
    selected = candidates[0]

    # The rendered homepage card can sit inside a large section containing
    # multiple stories, so its nearest image is not reliably the selected
    # headline's image. Resolve image metadata from the selected article page.
    article_page_image = find_page_image_url(selected.link)

    final_image = article_page_image or selected.image_url

    print(f'SELECTED CNN FINAL LEAD: "{selected.title}"')
    print(f"CNN FINAL LEAD LINK: {selected.link}")
    print(f"CNN FINAL LEAD IMAGE: {final_image}")

    return {
        "source": source_key,
        "title": selected.title,
        "link": selected.link,
        "url": selected.link,
        "summary": "",
        "image": final_image,
        "image_url": final_image,
        "published": "",
    }


def fetch_ranked_candidates(source_key):
    source_key = normalize_source_key(source_key)

    if source_key == "CNN":
        return (
            "CNN",
            "CNN",
            fetch_cnn_rendered_homepage_candidates(),
        )

    return _GENERIC_FETCH_RANKED_CANDIDATES(source_key)


def fetch_source_specific_homepage_lead_article(source_key):
    source_key = normalize_source_key(source_key)

    if source_key == "CNN":
        return fetch_cnn_homepage_lead_article("CNN")

    if source_key in {"FOX", "FOXNEWS"}:
        return fetch_fox_homepage_lead_article("FOX")

    raise RuntimeError(
        f"No source-specific homepage resolver for {source_key}"
    )



# ============================================================
# CNN rendered homepage in-memory cache
# ============================================================

_CNN_RENDERED_UNCACHED = fetch_cnn_rendered_homepage_candidates
_CNN_RENDERED_CANDIDATES_CACHE = []
_CNN_RENDERED_CANDIDATES_CACHE_SAVED_AT = 0.0
_CNN_RENDERED_CANDIDATES_CACHE_TTL_SECONDS = 120
_CNN_RENDERED_CANDIDATES_CACHE_LOCK = threading.Condition()
_CNN_RENDERED_CANDIDATES_FETCHING = False


def fetch_cnn_rendered_homepage_candidates():
    global _CNN_RENDERED_CANDIDATES_CACHE
    global _CNN_RENDERED_CANDIDATES_CACHE_SAVED_AT
    global _CNN_RENDERED_CANDIDATES_FETCHING

    with _CNN_RENDERED_CANDIDATES_CACHE_LOCK:
        cache_age = (
            time.monotonic()
            - _CNN_RENDERED_CANDIDATES_CACHE_SAVED_AT
        )

        if (
            _CNN_RENDERED_CANDIDATES_CACHE
            and cache_age < _CNN_RENDERED_CANDIDATES_CACHE_TTL_SECONDS
        ):
            print(
                "Using cached rendered CNN homepage candidates "
                f"({cache_age:.0f}s old)."
            )
            return list(_CNN_RENDERED_CANDIDATES_CACHE)

        if _CNN_RENDERED_CANDIDATES_FETCHING:
            print(
                "Waiting for the active CNN homepage render to finish..."
            )

            _CNN_RENDERED_CANDIDATES_CACHE_LOCK.wait(timeout=35)

            cache_age = (
                time.monotonic()
                - _CNN_RENDERED_CANDIDATES_CACHE_SAVED_AT
            )

            if (
                _CNN_RENDERED_CANDIDATES_CACHE
                and cache_age < _CNN_RENDERED_CANDIDATES_CACHE_TTL_SECONDS
            ):
                print(
                    "Using CNN homepage candidates produced by "
                    "the concurrent request."
                )
                return list(_CNN_RENDERED_CANDIDATES_CACHE)

        _CNN_RENDERED_CANDIDATES_FETCHING = True

    try:
        candidates = _CNN_RENDERED_UNCACHED()

        with _CNN_RENDERED_CANDIDATES_CACHE_LOCK:
            _CNN_RENDERED_CANDIDATES_CACHE = list(candidates)
            _CNN_RENDERED_CANDIDATES_CACHE_SAVED_AT = time.monotonic()
            _CNN_RENDERED_CANDIDATES_FETCHING = False
            _CNN_RENDERED_CANDIDATES_CACHE_LOCK.notify_all()

        if candidates:
            print(
                "CNN rendered homepage cache refreshed: "
                f'lead="{candidates[0].title}"'
            )

        return list(candidates)

    except Exception:
        with _CNN_RENDERED_CANDIDATES_CACHE_LOCK:
            _CNN_RENDERED_CANDIDATES_FETCHING = False
            _CNN_RENDERED_CANDIDATES_CACHE_LOCK.notify_all()

        raise
