import html
import json
import os
import re
import ssl
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from difflib import SequenceMatcher

import certifi


@dataclass
class NewsArticle:
    title: str
    source: str
    image_url: str = ""
    link: str = ""
    image_bytes: bytes = b""


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

# Temporary debug targets. These are used to score candidate extraction during this
# current headline debugging pass. They are not used unless the source returns
# candidates; they help the fetcher choose the actual lead-story candidate instead
# of a market/live/blog/sidebar item.
EXPECTED_HEADLINES = {
    "FOX": "Iran Security Council confirms immediate end to war in effect after Trump announces deal reached",
    "CNBC": "U.S. and Iran agree on peace deal to end the war, Trump and Pakistan say",
    "CNN": "Trump and Iran reach agreement that includes opening Strait of Hormuz",
    "BLOOMBERG": "US and Iran Reach Deal to Halt the War, Reopen Hormuz",
    "NEWSMAX": "Iran Deal Done, Strait to Open",
    "NYTIMES": "U.S. and Iran Reach Cease-Fire Agreement",
    "REUTERS": "US, Iran reach agreement to end war, signing set for Friday",
    "TIMESOFISRAEL": "US, Iran confirm deal reached to end war; Trump: Hormuz to open, US blockade to end",
    "BBC": "US and Iran announce deal to end military operations as Trump says 'let the oil flow!'",
    "APNEWS": "A tentative deal is reached to end the Iran war and Trump orders a stop to the US naval blockade",
}

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
    target = normalize_text(EXPECTED_HEADLINES.get(source_key, ""))
    terms = set(target.split())
    always_important = {
        "iran",
        "us",
        "trump",
        "pakistan",
        "deal",
        "cease",
        "ceasefire",
        "war",
        "hormuz",
        "strait",
        "blockade",
        "military",
        "operations",
        "friday",
        "oil",
        "flow",
        "security",
        "council",
    }
    return terms | always_important


def score_candidate(candidate, source_key):
    target = EXPECTED_HEADLINES.get(source_key, "")
    normalized_title = normalize_text(candidate.title)
    normalized_target = normalize_text(target)

    if not normalized_title:
        return -10000

    score = 0.0

    if normalized_target:
        score += SequenceMatcher(None, normalized_title, normalized_target).ratio() * 100

        target_words = set(normalized_target.split())
        title_words = set(normalized_title.split())

        if target_words:
            score += (len(title_words & target_words) / max(1, len(target_words))) * 160

        important_terms = target_terms_for_source(source_key)
        score += len(title_words & important_terms) * 18

    # Strong current-story signals that should outrank sidebars and market updates.
    phrase_bonuses = [
        ("iran", 70),
        ("hormuz", 100),
        ("strait", 60),
        ("peace deal", 120),
        ("cease fire", 95),
        ("ceasefire", 95),
        ("end war", 110),
        ("end the war", 110),
        ("halt the war", 120),
        ("reopen", 80),
        ("blockade", 90),
        ("pakistan", 75),
        ("trump", 50),
        ("oil flow", 100),
        ("let the oil flow", 160),
    ]

    for phrase, points in phrase_bonuses:
        if phrase in normalized_title:
            score += points

    # Earlier homepage/RSS position is still a tie-breaker, but it should not beat
    # the correct story when a lower page card appears first.
    if candidate.origin.startswith("homepage"):
        score += max(0, 100000 - min(candidate.position, 100000)) / 2500
    elif candidate.origin.startswith("rss"):
        score += max(0, 200 - min(candidate.position, 200)) / 4

    if is_bad_market_live_title(candidate.title):
        score -= 350

    if source_key == "FOX":
        link_lower = (candidate.link or "").lower()
        title_lower = normalize_text(candidate.title)

        if "iran security council issues statement" in title_lower:
            score += 1200

        if "security council" in title_lower:
            score += 700

        if "deal has been completed" in title_lower:
            score += 500

        if "foxnews.com/live-news/trump-iran-war-peace-talks-pakistan-june-14" in link_lower:
            score += 900

        if "foxnews.com/live-news/" in link_lower:
            score += 500

        if "let the oil flow" in title_lower:
            score -= 450

        if "/video/" in link_lower:
            score -= 500

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


def fetch_homepage_candidates(source_key):
    config = NEWS_SOURCES[source_key]
    source_name = config["source_name"]
    homepage_url = config["homepage"]
    allowed_domain_text = config["allowed_domain"]

    print(f"Trying {source_name} homepage: {homepage_url}")
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
    # Fast headline first, but still try one quick image lookup if the selected
    # candidate did not include an image URL.
    if not article.image_url and article.link:
        article.image_url = find_page_image_url(article.link)

    if article.image_url:
        article.image_bytes = download_image_bytes(article.image_url)

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

    if not candidates:
        raise RuntimeError("No usable headline candidates found")

    for candidate in candidates:
        score_candidate(candidate, source_key)

    candidates.sort(key=lambda item: item.score, reverse=True)
    return candidates[0]


def fetch_configured_article(source_key):
    if source_key not in NEWS_SOURCES:
        print(f"Unknown news source key {source_key}; falling back to FOX NEWS")
        source_key = "FOX"

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

    try:
        best = choose_best_candidate(source_key, all_candidates)
        print(
            f"SELECTED {source_name}: score={best.score:.1f} "
            f"origin={best.origin} title={best.title}"
        )
        article = enrich_article(build_article_from_candidate(best))
        cache_article(source_key, article)
        return article
    except Exception as error:
        errors.append(str(error))
        print(f"{source_name} selection failed: {error}")

    return fallback_article(source_key, " | ".join(errors))


def fetch_news_cards(left_source_key="FOX", right_source_key="CNBC"):
    # Fetch left and right in parallel so a slow optional source does not block the
    # other article card.
    with ThreadPoolExecutor(max_workers=2) as executor:
        left_future = executor.submit(fetch_configured_article, left_source_key)
        right_future = executor.submit(fetch_configured_article, right_source_key)

        left_article = left_future.result()
        right_article = right_future.result()

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
