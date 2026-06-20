import html
import json
import re
import ssl
import urllib.request
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

import certifi


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


def fetch_article_text_payload(url):
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
