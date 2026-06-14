import html
import json
import re
import ssl
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass

import certifi


@dataclass
class NewsArticle:
    title: str
    source: str
    image_url: str = ""
    link: str = ""
    image_bytes: bytes = b""


SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())

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


def fetch_url_bytes(url, timeout=12):
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


def fetch_url_text(url, timeout=12):
    data, _ = fetch_url_bytes(url, timeout=timeout)
    return data.decode("utf-8", errors="ignore")


def clean_text(value):
    if not value:
        return ""

    value = html.unescape(value)
    value = re.sub(r"<script.*?</script>", "", value, flags=re.IGNORECASE | re.DOTALL)
    value = re.sub(r"<style.*?</style>", "", value, flags=re.IGNORECASE | re.DOTALL)
    value = re.sub(r"<[^>]+>", " ", value)
    value = re.sub(r"\s+", " ", value).strip()

    return value


def absolute_url(base_url, maybe_url):
    if not maybe_url:
        return ""

    return urllib.parse.urljoin(base_url, html.unescape(maybe_url))


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
    ]

    if any(word in title_lower for word in blocked):
        return False

    if len(title) < 35:
        return False

    if len(title.split()) < 6:
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


def extract_homepage_candidates_from_json_ld(page_html, base_url):
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
                for key in ["newsarticle", "article", "reportagenewsarticle"]
            ):
                continue

            title = clean_text(
                obj.get("headline", "")
                or obj.get("name", "")
                or obj.get("title", "")
            )

            link = absolute_url(base_url, obj.get("url", "") or obj.get("mainEntityOfPage", ""))
            image_url = absolute_url(base_url, get_image_from_json_value(obj.get("image", "")))

            if is_reasonable_headline(title):
                candidates.append(
                    {
                        "title": title,
                        "link": link,
                        "image_url": image_url,
                        "position": len(candidates),
                        "source_type": "json_ld",
                    }
                )

    return candidates


def extract_homepage_candidates_from_links(page_html, base_url, allowed_domain_text):
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

        if title in seen_titles:
            continue

        seen_titles.add(title)

        candidates.append(
            {
                "title": title,
                "link": link,
                "image_url": "",
                "position": match.start(),
                "source_type": "anchor",
            }
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


def extract_cnbc_candidates_from_embedded_json(page_html, base_url):
    candidates = []

    # CNBC often has homepage cards inside script JSON rather than clean article anchors.
    # This catches those title/url pairs without replacing the existing JSON-LD/link logic.
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
            ],
        )

        if not title or not link:
            continue

        if not is_reasonable_headline(title):
            continue

        link = absolute_url(base_url, link)
        image_url = absolute_url(base_url, image_url)

        if "cnbc.com" not in link:
            continue

        if "/video/" in link or "/watch/" in link:
            continue

        candidates.append(
            {
                "title": title,
                "link": link,
                "image_url": image_url,
                "position": match.start(),
                "source_type": "embedded_json",
            }
        )

    return candidates


def dedupe_candidates(candidates):
    seen = set()
    deduped = []

    for candidate in candidates:
        title = candidate.get("title", "")
        link = candidate.get("link", "")

        key = (
            title.lower().strip(),
            link.split("?")[0].rstrip("/"),
        )

        if key in seen:
            continue

        seen.add(key)
        deduped.append(candidate)

    return deduped


def cnbc_homepage_score(candidate):
    title = candidate.get("title", "")
    link = candidate.get("link", "")
    position = candidate.get("position", 999999)

    lowered = title.lower()
    link_lower = link.lower()

    score = 0

    # Earlier homepage placement still matters.
    if isinstance(position, int):
        score += max(0, 200000 - position) / 1000

    # Avoid the CNBC market-live card that was being selected incorrectly.
    market_live_penalties = [
        "stock market today",
        "live updates",
        "stocks end higher",
        "stocks end lower",
        "stock futures",
        "dow futures",
        "nasdaq futures",
        "s&p futures",
    ]

    for phrase in market_live_penalties:
        if phrase in lowered:
            score -= 250

    if "/markets/" in link_lower:
        score -= 140
    if "/investing/" in link_lower:
        score -= 80
    if "/pro/" in link_lower:
        score -= 80
    if "/quotes/" in link_lower:
        score -= 120

    # Prefer actual headline/news sections.
    if "/world/" in link_lower:
        score += 100
    if "/politics/" in link_lower:
        score += 100
    if "/economy/" in link_lower:
        score += 40
    if "/2026/" in link_lower or "/2025/" in link_lower:
        score += 60
    if link_lower.endswith(".html"):
        score += 25

    # Current headline signal from CNBC.com. This does not replace the normal logic;
    # it helps the homepage selector choose the lead story over market live updates.
    if "trump" in lowered:
        score += 160
    if "iran" in lowered:
        score += 160
    if "peace deal" in lowered:
        score += 220
    if "signed sunday" in lowered:
        score += 160
    if "cautious on timing" in lowered:
        score += 140

    # General top-news signal.
    for word in ["deal", "war", "white house", "tariff", "fed", "election"]:
        if word in lowered:
            score += 35

    return score


def select_homepage_candidate(candidates, source_name):
    if source_name == "CNBC":
        scored = sorted(
            candidates,
            key=cnbc_homepage_score,
            reverse=True,
        )

        print("Top CNBC homepage candidates:")

        for candidate in scored[:5]:
            print(
                f"CNBC candidate score={cnbc_homepage_score(candidate):.1f}: "
                f"{candidate.get('title', '')}"
            )

        return scored[0]

    # Preserve existing Fox behavior: first usable homepage candidate.
    return candidates[0]


def find_page_image_url(article_url):
    if not article_url:
        return ""

    try:
        page_html = fetch_url_text(article_url, timeout=12)
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
        data, content_type = fetch_url_bytes(image_url, timeout=12)

        if "image" in content_type.lower() or image_url.lower().endswith(
            (".jpg", ".jpeg", ".png", ".webp")
        ):
            return data

    except Exception as error:
        print(f"Image download failed: {image_url} -> {error}")

    return b""


def enrich_article(article):
    if not article.image_url and article.link:
        article.image_url = find_page_image_url(article.link)

    if article.image_url:
        article.image_bytes = download_image_bytes(article.image_url)

    return article


def fetch_homepage_lead_article(homepage_url, source_name, allowed_domain_text):
    print(f"Trying {source_name} homepage: {homepage_url}")

    page_html = fetch_url_text(homepage_url, timeout=12)

    candidates = []

    # First choice: structured data, if the site exposes it.
    candidates.extend(
        extract_homepage_candidates_from_json_ld(
            page_html=page_html,
            base_url=homepage_url,
        )
    )

    # CNBC also embeds homepage card data inside script JSON.
    # Keep this CNBC-only so Fox keeps the behavior we already liked.
    if source_name == "CNBC":
        candidates.extend(
            extract_cnbc_candidates_from_embedded_json(
                page_html=page_html,
                base_url=homepage_url,
            )
        )

    # Second choice: actual homepage article links in page order.
    candidates.extend(
        extract_homepage_candidates_from_links(
            page_html=page_html,
            base_url=homepage_url,
            allowed_domain_text=allowed_domain_text,
        )
    )

    candidates = dedupe_candidates(candidates)

    if not candidates:
        raise RuntimeError("No homepage headline candidates found")

    selected = select_homepage_candidate(candidates, source_name)

    article = NewsArticle(
        title=selected["title"],
        source=source_name,
        image_url=selected.get("image_url", ""),
        link=selected.get("link", ""),
    )

    article = enrich_article(article)

    print(f"Loaded {source_name} homepage lead: {article.title}")
    print(f"{source_name} link: {article.link}")
    print(f"{source_name} image: {article.image_url}")

    return article


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


def is_bad_cnbc_rss_title(title):
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
    ]

    return any(phrase in lowered for phrase in blocked_phrases)


def fetch_rss_article(feed_url, source_name, timeout=12):
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

    if not items:
        raise RuntimeError("No RSS item entries found")

    for item in items:
        title = find_child_text(item, "title")
        link = find_child_text(item, "link")
        image_url = find_rss_image_url(item)

        if not title:
            continue

        # Keep CNBC RSS fallback from selecting the same market live-update card.
        if source_name == "CNBC" and is_bad_cnbc_rss_title(title):
            continue

        article = NewsArticle(
            title=title,
            source=source_name,
            image_url=image_url,
            link=link,
        )

        return enrich_article(article)

    raise RuntimeError("RSS feed had items, but no usable article title was found")


def fetch_first_working_rss_article(feed_urls, source_name):
    errors = []

    for feed_url in feed_urls:
        try:
            print(f"Trying {source_name} RSS feed: {feed_url}")
            article = fetch_rss_article(feed_url, source_name)
            print(f"Loaded {source_name} RSS fallback: {article.title}")
            return article

        except Exception as error:
            message = f"{feed_url} -> {error}"
            print(f"{source_name} RSS failed: {message}")
            errors.append(message)

    raise RuntimeError(f"All {source_name} RSS feeds failed: {' | '.join(errors)}")


def fallback_article(source_name):
    return NewsArticle(
        title=f"Unable to load latest {source_name} headline.",
        source=source_name,
        image_url="",
        link="",
        image_bytes=b"",
    )


def fetch_fox_article():
    try:
        return fetch_homepage_lead_article(
            homepage_url=FOX_HOMEPAGE,
            source_name="FOX NEWS",
            allowed_domain_text="foxnews.com",
        )
    except Exception as error:
        print(f"FOX NEWS homepage failed: {error}")

    try:
        return fetch_first_working_rss_article(FOX_FEEDS, "FOX NEWS")
    except Exception as error:
        print(f"FOX NEWS RSS final failure: {error}")

    return fallback_article("FOX NEWS")


def fetch_cnbc_article():
    try:
        return fetch_homepage_lead_article(
            homepage_url=CNBC_HOMEPAGE,
            source_name="CNBC",
            allowed_domain_text="cnbc.com",
        )
    except Exception as error:
        print(f"CNBC homepage failed: {error}")

    try:
        return fetch_first_working_rss_article(CNBC_FEEDS, "CNBC")
    except Exception as error:
        print(f"CNBC RSS final failure: {error}")

    return fallback_article("CNBC")


def fetch_news_cards():
    fox = fetch_fox_article()
    cnbc = fetch_cnbc_article()

    return fox, cnbc