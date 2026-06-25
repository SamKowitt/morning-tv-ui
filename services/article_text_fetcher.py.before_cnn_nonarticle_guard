import html
import json
import re
import ssl
import urllib.request
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

import certifi
from services.newsmax_chrome import fetch_newsmax_article_payload


SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125.0 Safari/537.36"
)


def clean_text(value):
    value = html.unescape(str(value or ""))
    value = re.sub(r"<script.*?</script>", " ", value, flags=re.IGNORECASE | re.DOTALL)
    value = re.sub(r"<style.*?</style>", " ", value, flags=re.IGNORECASE | re.DOTALL)
    value = re.sub(r"<[^>]+>", " ", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def fetch_url_text(url, timeout=20):
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Cache-Control": "no-cache",
        },
    )

    def read_with_context(context=None):
        with urllib.request.urlopen(request, timeout=timeout, context=context or SSL_CONTEXT) as response:
            data = response.read()
            encoding = response.headers.get_content_charset() or "utf-8"
            return data.decode(encoding, errors="replace")

    try:
        return read_with_context()
    except Exception as error:
        text = str(error)
        reason = str(getattr(error, "reason", ""))

        if (
            "CERTIFICATE_VERIFY_FAILED" in text
            or "CERTIFICATE_VERIFY_FAILED" in reason
            or "certificate verify failed" in text.lower()
            or "certificate verify failed" in reason.lower()
        ):
            return read_with_context(ssl._create_unverified_context())

        raise


def flatten_json(value):
    found = []

    if isinstance(value, dict):
        found.append(value)
        for child in value.values():
            found.extend(flatten_json(child))
    elif isinstance(value, list):
        for child in value:
            found.extend(flatten_json(child))

    return found


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
            objects.append(json.loads(raw))
        except Exception:
            continue

    return objects


def extract_article_body_from_json_ld(page_html):
    bodies = []

    for root in extract_json_ld_objects(page_html):
        for obj in flatten_json(root):
            if not isinstance(obj, dict):
                continue

            obj_type = obj.get("@type", "")
            if isinstance(obj_type, list):
                obj_type = " ".join(str(item) for item in obj_type)

            obj_type = str(obj_type).lower()
            article_like = any(key in obj_type for key in ["newsarticle", "article", "reportagenewsarticle"])

            body = obj.get("articleBody", "") or obj.get("text", "")

            if article_like and body:
                cleaned = clean_text(body)
                if is_valid_article_text(cleaned):
                    bodies.append(cleaned)

    bodies.sort(key=len, reverse=True)
    return bodies[0] if bodies else ""


class ParagraphExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_script = False
        self.in_style = False
        self.in_p = False
        self.current = []
        self.paragraphs = []

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()

        if tag == "script":
            self.in_script = True
        elif tag == "style":
            self.in_style = True
        elif tag == "p" and not self.in_script and not self.in_style:
            self.in_p = True
            self.current = []

    def handle_endtag(self, tag):
        tag = tag.lower()

        if tag == "script":
            self.in_script = False
        elif tag == "style":
            self.in_style = False
        elif tag == "p" and self.in_p:
            text = clean_text(" ".join(self.current))
            if text:
                self.paragraphs.append(text)

            self.in_p = False
            self.current = []

    def handle_data(self, data):
        if self.in_p and not self.in_script and not self.in_style:
            self.current.append(data)


def looks_like_article_paragraph(text):
    text = clean_text(text)
    lowered = text.lower()

    if len(text) < 45:
        return False

    bad = [
        "subscribe",
        "sign up",
        "newsletter",
        "all rights reserved",
        "click here",
        "download the app",
        "terms of use",
        "privacy policy",
        "advertisement",
        "this material may not be published",
        "fox news channel offers its audiences",
    ]

    if any(item in lowered for item in bad):
        return False

    return any(mark in text for mark in [".", "?", "!", "”", '"'])


def extract_article_text_from_paragraphs(page_html):
    parser = ParagraphExtractor()
    parser.feed(page_html)

    paragraphs = []
    seen = set()

    for paragraph in parser.paragraphs:
        paragraph = clean_text(paragraph)
        key = paragraph.lower()

        if key in seen:
            continue

        seen.add(key)

        if looks_like_article_paragraph(paragraph):
            paragraphs.append(paragraph)

    return clean_text(" ".join(paragraphs))


def is_valid_article_text(text):
    cleaned = clean_text(text)

    if len(cleaned) < 160:
        return False

    lowered = cleaned.lower()

    boilerplate = [
        "fox news channel offers its audiences",
        "as an alternative to the left-of-center offerings",
        "all rights reserved",
        "fox news network, llc",
        "privacy policy",
        "terms of use",
        "download the app",
        "subscribe to fox news",
    ]

    if any(phrase in lowered for phrase in boilerplate):
        return False

    sentence_marks = cleaned.count(".") + cleaned.count("?") + cleaned.count("!")
    return sentence_marks >= 2


class LiveUpdateHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_script = False
        self.in_style = False
        self.capture_depth = 0
        self.current_tag = ""
        self.parts = []
        self.time_parts = []
        self.heading_parts = []

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        self.current_tag = tag

        if tag == "script":
            self.in_script = True
            return

        if tag == "style":
            self.in_style = True
            return

        if self.in_script or self.in_style:
            return

        if tag in {"p", "h1", "h2", "h3", "h4", "blockquote", "li", "time"}:
            self.capture_depth += 1

    def handle_endtag(self, tag):
        tag = tag.lower()

        if tag == "script":
            self.in_script = False
            return

        if tag == "style":
            self.in_style = False
            return

        if tag in {"p", "h1", "h2", "h3", "h4", "blockquote", "li", "time"} and self.capture_depth > 0:
            self.capture_depth -= 1

        self.current_tag = ""

    def handle_data(self, data):
        if self.in_script or self.in_style:
            return

        value = clean_text(data)
        if not value or self.capture_depth <= 0:
            return

        if self.current_tag == "time":
            self.time_parts.append(value)
        elif self.current_tag in {"h1", "h2", "h3", "h4"}:
            self.heading_parts.append(value)
        else:
            self.parts.append(value)


def strip_fragment_to_live_update(fragment):
    parser = LiveUpdateHTMLParser()
    parser.feed(fragment)

    heading = clean_text(" ".join(parser.heading_parts))
    time_text = clean_text(" ".join(parser.time_parts))

    parts = []
    seen = set()

    for part in parser.parts:
        part = clean_text(part)
        key = part.lower()

        if not part or key in seen:
            continue

        seen.add(key)

        if looks_like_article_paragraph(part):
            parts.append(part)

    body = clean_text(" ".join(parts))

    if len(body) < 80:
        return None

    lowered = body.lower()

    bad = [
        "click here to download the fox news app",
        "this material may not be published",
        "all rights reserved",
        "fox news network, llc",
        "subscribe to fox news",
        "download the app",
        "privacy policy",
        "terms of use",
    ]

    if any(phrase in lowered for phrase in bad):
        return None

    return {
        "time": time_text,
        "heading": heading,
        "text": body,
    }


def extract_live_update_items_from_article_tags(page_html):
    blocks = re.findall(
        r"<article\b[^>]*>.*?</article>",
        page_html,
        flags=re.IGNORECASE | re.DOTALL,
    )

    if not blocks:
        patterns = [
            r"<div\b[^>]+class=[\"'][^\"']*(?:live|update|post|article|story)[^\"']*[\"'][^>]*>.*?</div>",
            r"<section\b[^>]+class=[\"'][^\"']*(?:live|update|post|article|story)[^\"']*[\"'][^>]*>.*?</section>",
        ]

        for pattern in patterns:
            blocks.extend(re.findall(pattern, page_html, flags=re.IGNORECASE | re.DOTALL))

    updates = []
    seen = set()

    for block in blocks:
        update = strip_fragment_to_live_update(block)

        if not update:
            continue

        key = update["text"].lower()

        if key in seen:
            continue

        seen.add(key)
        updates.append(update)

    return updates if len(updates) > 1 else []


def format_live_update(update, limit=2000):
    time_text = clean_text(update.get("time", ""))
    heading = clean_text(update.get("heading", ""))
    body = clean_text(update.get("text", ""))

    pieces = []

    if time_text:
        pieces.append(time_text)

    if heading and heading.lower() not in body.lower():
        pieces.append(heading)

    pieces.append(body)

    combined = clean_text(" — ".join(piece for piece in pieces if piece))

    if len(combined) > limit:
        shortened = combined[:limit]
        split_at = max(shortened.rfind(". "), shortened.rfind("? "), shortened.rfind("! "), shortened.rfind(" "))

        if split_at > int(limit * 0.60):
            shortened = shortened[:split_at + 1]

        combined = shortened.strip() + "..."

    return combined



def fetch_espn_article_payload(url):
    """
    ESPN article pages need the rendered browser page rather than urllib HTML.
    """
    from services.newsmax_chrome import _close_page, _create_page, _eval, _navigate

    target_id = ""
    ws_url = ""

    try:
        target_id, ws_url = _create_page()
        _navigate(ws_url, url)

        payload = _eval(
            ws_url,
            r"""
(() => {
    const clean = value => String(value || "")
        .replace(/\s+/g, " ")
        .trim();

    const blockedBits = [
        "javascript is disabled",
        "enable javascript",
        "privacy preference center",
        "strictly necessary cookies",
        "functional cookies",
        "analytics cookies",
        "marketing cookies",
        "manage consent preferences",
        "advertisement",
        "sign up for",
        "follow us",
        "all rights reserved",
        "skip to main content"
    ];

    const usable = value => {
        const text = clean(value);

        if (text.length < 45) return false;

        const lowered = text.toLowerCase();
        return !blockedBits.some(bit => lowered.includes(bit));
    };

    const headlineNode =
        document.querySelector("article h1") ||
        document.querySelector("main h1") ||
        document.querySelector("h1");

    const headline = clean(
        headlineNode
            ? (headlineNode.innerText || headlineNode.textContent)
            : ""
    );

    const roots = [
        document.querySelector(".article-body"),
        document.querySelector("article .article-body"),
        document.querySelector('[data-id="article-body"]'),
        document.querySelector('[class*="article-body"]'),
        document.querySelector('[class*="ArticleBody"]'),
        document.querySelector("article"),
        document.querySelector("main")
    ].filter(Boolean);

    const root = roots[0] || document.body;

    const seen = new Set();
    const paragraphs = [];

    for (const node of root.querySelectorAll("p")) {
        const paragraph = clean(node.innerText || node.textContent);
        const key = paragraph.toLowerCase();

        if (!usable(paragraph) || seen.has(key)) {
            continue;
        }

        seen.add(key);
        paragraphs.push(paragraph);
    }

    let articleText = paragraphs.join("\n\n").trim();

    if (articleText.length < 180) {
        const rawText = String(
            root.innerText ||
            root.textContent ||
            ""
        ).trim();

        const lines = rawText
            .split(/\n+/)
            .map(clean)
            .filter(line => line.length >= 45);

        const seenLines = new Set();
        const articleLines = [];

        for (const line of lines) {
            const key = line.toLowerCase();

            if (seenLines.has(key)) {
                continue;
            }

            seenLines.add(key);
            articleLines.push(line);
        }

        articleText = articleLines.join("\n\n").trim();

        if (articleText.length < 180 && rawText.length >= 180) {
            articleText = clean(rawText);
        }
    }

    return {
        headline,
        text: articleText,
        paragraphCount: paragraphs.length,
        pageTitle: document.title || ""
    };
})()
""",
            timeout=25,
        )

        if not isinstance(payload, dict):
            raise RuntimeError("Chrome did not return an ESPN article payload")

        article_text = clean_text(payload.get("text", ""))

        if not is_valid_article_text(article_text):
            raise RuntimeError(
                "No readable ESPN article text found. "
                f"Page title: {payload.get('pageTitle', '')!r}; "
                f"paragraphs: {payload.get('paragraphCount', 0)!r}"
            )

        print(
            "ESPN CHROME ARTICLE TEXT: "
            f"{len(article_text)} chars | "
            f"{payload.get('paragraphCount', 0)} paragraphs"
        )

        return {
            "is_live": False,
            "method": "espn_chrome",
            "text": article_text,
            "updates": [],
            "headline": clean_text(payload.get("headline", "")),
        }

    finally:
        if target_id:
            _close_page(target_id)


def _fetch_article_text_payload_uncached(url):
    parsed_url = urlparse(str(url or ""))
    hostname = parsed_url.netloc.lower()

    # Newsmax must use Chrome because direct HTTP requests stall on this Mac.
    if hostname == "newsmax.com" or hostname.endswith(".newsmax.com"):
        return fetch_newsmax_article_payload(url)

    # ESPN serves a script/anti-bot shell to ordinary urllib requests.
    if hostname == "espn.com" or hostname.endswith(".espn.com"):
        return fetch_espn_article_payload(url)

    page_html = fetch_url_text(url, timeout=20)
    is_live = "/live-news/" in str(url).lower()

    if is_live:
        live_updates = extract_live_update_items_from_article_tags(page_html)

        if live_updates:
            formatted_updates = [format_live_update(update, limit=2000) for update in live_updates]
            return {
                "is_live": True,
                "method": "live_update_blocks",
                "text": "\n\n".join(formatted_updates),
                "updates": formatted_updates,
            }

    text = extract_article_body_from_json_ld(page_html)

    if not text:
        text = extract_article_text_from_paragraphs(page_html)

    return {
        "is_live": is_live,
        "method": "json_ld_articleBody" if text else "none",
        "text": clean_text(text),
        "updates": [],
    }


# ============================================================
# Article text cache and background preload support
# ============================================================
import hashlib
import os
import tempfile
import threading
import time
from pathlib import Path


ARTICLE_TEXT_CACHE_FILE = Path.home() / ".morning_tv_ui_article_text_cache.json"
ARTICLE_TEXT_CACHE_LOCK = threading.Lock()
ARTICLE_TEXT_CACHE = None
ARTICLE_TEXT_PREFETCHING = set()

# Normal articles keep cached text for seven days.
# Live-news articles are refreshed much more often.
NORMAL_ARTICLE_CACHE_SECONDS = 7 * 24 * 60 * 60
LIVE_ARTICLE_CACHE_SECONDS = 10 * 60


def _article_cache_key(url):
    normalized = str(url or "").strip()
    normalized = normalized.split("#", 1)[0]
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _load_article_text_cache():
    global ARTICLE_TEXT_CACHE

    if ARTICLE_TEXT_CACHE is not None:
        return ARTICLE_TEXT_CACHE

    try:
        raw = ARTICLE_TEXT_CACHE_FILE.read_text(encoding="utf-8")
        loaded = json.loads(raw)

        if not isinstance(loaded, dict):
            loaded = {}
    except Exception:
        loaded = {}

    ARTICLE_TEXT_CACHE = loaded
    return ARTICLE_TEXT_CACHE


def _save_article_text_cache():
    cache = _load_article_text_cache()

    try:
        ARTICLE_TEXT_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)

        # Keep the cache from growing forever.
        entries = list(cache.items())
        entries.sort(
            key=lambda item: float(item[1].get("saved_at", 0) or 0),
            reverse=True,
        )

        trimmed = dict(entries[:80])

        fd, temp_path = tempfile.mkstemp(
            prefix=".morning_tv_ui_article_text_cache_",
            suffix=".json",
            dir=str(ARTICLE_TEXT_CACHE_FILE.parent),
        )

        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(trimmed, handle, ensure_ascii=False, indent=2)

            os.replace(temp_path, ARTICLE_TEXT_CACHE_FILE)
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

        cache.clear()
        cache.update(trimmed)

    except Exception as error:
        print(f"Article text cache save failed: {error}")


def _cache_lifetime(payload):
    if bool((payload or {}).get("is_live")):
        return LIVE_ARTICLE_CACHE_SECONDS

    return NORMAL_ARTICLE_CACHE_SECONDS


def get_cached_article_text_payload(url):
    if not url:
        return None

    key = _article_cache_key(url)

    with ARTICLE_TEXT_CACHE_LOCK:
        cache = _load_article_text_cache()
        record = cache.get(key)

        if not isinstance(record, dict):
            return None

        saved_at = float(record.get("saved_at", 0) or 0)
        payload = record.get("payload")

        if not isinstance(payload, dict):
            return None

        if (time.time() - saved_at) > _cache_lifetime(payload):
            cache.pop(key, None)
            return None

        text = str(payload.get("text", "") or "")

        if len(text.strip()) < 80:
            return None

        return dict(payload)


def _store_cached_article_text_payload(url, payload):
    if not url or not isinstance(payload, dict):
        return

    text = str(payload.get("text", "") or "")

    if len(text.strip()) < 80:
        return

    key = _article_cache_key(url)

    with ARTICLE_TEXT_CACHE_LOCK:
        cache = _load_article_text_cache()

        cache[key] = {
            "url": str(url),
            "saved_at": time.time(),
            "payload": dict(payload),
        }

        _save_article_text_cache()


def fetch_article_text_payload(url):
    cached = get_cached_article_text_payload(url)

    if cached:
        print(f"ARTICLE TEXT CACHE HIT: {url}")
        return cached

    payload = _fetch_article_text_payload_uncached(url)
    _store_cached_article_text_payload(url, payload)

    return payload


def prefetch_article_text_payload(url):
    url = str(url or "").strip()

    if not url:
        return

    if get_cached_article_text_payload(url):
        print(f"ARTICLE TEXT ALREADY CACHED: {url}")
        return

    with ARTICLE_TEXT_CACHE_LOCK:
        if url in ARTICLE_TEXT_PREFETCHING:
            return

        ARTICLE_TEXT_PREFETCHING.add(url)

    def worker():
        try:
            print(f"PRELOADING ARTICLE TEXT: {url}")
            payload = fetch_article_text_payload(url)

            text_length = len(str(payload.get("text", "") or ""))

            print(
                f"ARTICLE TEXT PRELOAD COMPLETE: "
                f"{text_length} chars | {url}"
            )

        except Exception as error:
            print(f"ARTICLE TEXT PRELOAD FAILED: {url} -> {error}")

        finally:
            with ARTICLE_TEXT_CACHE_LOCK:
                ARTICLE_TEXT_PREFETCHING.discard(url)

    threading.Thread(
        target=worker,
        name="MorningTVArticlePreload",
        daemon=True,
    ).start()


# ============================================================
# Prevent duplicate article fetches while a preload is running
# ============================================================
ARTICLE_TEXT_PREFETCH_EVENTS = {}
ARTICLE_TEXT_PREFETCH_EVENTS_LOCK = threading.Lock()


def fetch_article_text_payload(url):
    url = str(url or "").strip()

    cached = get_cached_article_text_payload(url)
    if cached and is_valid_article_text(cached.get("text", "")):
        print(f"ARTICLE TEXT CACHE HIT: {url}")
        return cached

    with ARTICLE_TEXT_PREFETCH_EVENTS_LOCK:
        event = ARTICLE_TEXT_PREFETCH_EVENTS.get(url)

    # A background preload is already working on this exact article.
    # Wait for that one instead of opening a duplicate Chrome page.
    if event is not None:
        print(f"ARTICLE TEXT WAITING FOR PRELOAD: {url}")
        event.wait(timeout=25)

        cached = get_cached_article_text_payload(url)
        if cached:
            print(f"ARTICLE TEXT CACHE HIT AFTER PRELOAD: {url}")
            return cached

    payload = _fetch_article_text_payload_uncached(url)
    _store_cached_article_text_payload(url, payload)
    return payload


def prefetch_article_text_payload(url):
    url = str(url or "").strip()

    if not url:
        return

    if get_cached_article_text_payload(url):
        print(f"ARTICLE TEXT ALREADY CACHED: {url}")
        return

    with ARTICLE_TEXT_PREFETCH_EVENTS_LOCK:
        existing = ARTICLE_TEXT_PREFETCH_EVENTS.get(url)

        if existing is not None:
            return

        event = threading.Event()
        ARTICLE_TEXT_PREFETCH_EVENTS[url] = event

    def worker():
        try:
            print(f"PRELOADING ARTICLE TEXT: {url}")

            cached = get_cached_article_text_payload(url)

            if cached:
                print(f"ARTICLE TEXT ALREADY CACHED: {url}")
                return

            payload = _fetch_article_text_payload_uncached(url)
            _store_cached_article_text_payload(url, payload)

            text_length = len(str(payload.get("text", "") or ""))

            print(
                f"ARTICLE TEXT PRELOAD COMPLETE: "
                f"{text_length} chars | {url}"
            )

        except Exception as error:
            print(f"ARTICLE TEXT PRELOAD FAILED: {url} -> {error}")

        finally:
            with ARTICLE_TEXT_PREFETCH_EVENTS_LOCK:
                done_event = ARTICLE_TEXT_PREFETCH_EVENTS.pop(url, None)

                if done_event:
                    done_event.set()

    threading.Thread(
        target=worker,
        name="MorningTVArticlePreload",
        daemon=True,
    ).start()
