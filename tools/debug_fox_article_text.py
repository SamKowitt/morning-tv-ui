import html
import json
import re
import ssl
import sys
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse


RAW_OUTPUT = Path("tools/fox_article_raw.html")
TEXT_OUTPUT = Path("tools/fox_article_text.txt")
FOX_HOME_RAW_OUTPUT = Path("tools/fox_homepage_for_article_debug.html")


USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125.0 Safari/537.36"
)


def clean_text(value):
    value = html.unescape(str(value or ""))
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
        if context is None:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                data = response.read()
                encoding = response.headers.get_content_charset() or "utf-8"
                return data.decode(encoding, errors="replace")

        with urllib.request.urlopen(request, timeout=timeout, context=context) as response:
            data = response.read()
            encoding = response.headers.get_content_charset() or "utf-8"
            return data.decode(encoding, errors="replace")

    try:
        return read_with_context()
    except Exception as error:
        error_text = str(error)
        reason_text = str(getattr(error, "reason", ""))

        if (
            isinstance(error, ssl.SSLCertVerificationError)
            or "CERTIFICATE_VERIFY_FAILED" in error_text
            or "CERTIFICATE_VERIFY_FAILED" in reason_text
            or "certificate verify failed" in error_text.lower()
            or "certificate verify failed" in reason_text.lower()
        ):
            print("SSL verification failed; retrying with relaxed SSL context.")
            return read_with_context(ssl._create_unverified_context())

        raise


def import_news_fetcher_module():
    """
    Import the app's news_fetcher.py regardless of whether it lives in
    services/news_fetcher.py, ui/services/news_fetcher.py, or another package folder.
    """
    import importlib.util

    project_root = Path.cwd()

    candidates = [
        project_root / "services" / "news_fetcher.py",
        project_root / "ui" / "services" / "news_fetcher.py",
        project_root / "src" / "services" / "news_fetcher.py",
        project_root / "news_fetcher.py",
    ]

    candidates.extend(project_root.rglob("news_fetcher.py"))

    seen = set()

    for candidate in candidates:
        candidate = candidate.resolve()

        if candidate in seen:
            continue

        seen.add(candidate)

        if not candidate.exists():
            continue

        print(f"Using news_fetcher module: {candidate}")

        spec = importlib.util.spec_from_file_location("debug_news_fetcher", candidate)
        module = importlib.util.module_from_spec(spec)

        if not spec or not spec.loader:
            continue

        spec.loader.exec_module(module)
        return module

    raise RuntimeError("Could not find news_fetcher.py anywhere in this project.")


def get_current_fox_article():
    """
    Uses the app's existing Fox headline selector.
    This keeps the debug script testing the same article your UI would navigate to.
    """
    module = import_news_fetcher_module()

    if hasattr(module, "fetch_configured_article"):
        try:
            article = module.fetch_configured_article("FOX")
            return article
        except Exception as error:
            print(f"fetch_configured_article('FOX') failed: {error}")

    if hasattr(module, "fetch_fox_article"):
        try:
            article = module.fetch_fox_article()
            return article
        except Exception as error:
            print(f"fetch_fox_article() failed: {error}")

    if hasattr(module, "fetch_fox_homepage_article"):
        try:
            article = module.fetch_fox_homepage_article()
            return article
        except Exception as error:
            print(f"fetch_fox_homepage_article() failed: {error}")

    raise RuntimeError("Found news_fetcher.py, but could not find a usable FOX fetch function.")


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

            article_like = any(
                key in obj_type
                for key in ["newsarticle", "article", "reportagenewsarticle", "liveblogposting"]
            )

            body = obj.get("articleBody", "") or obj.get("text", "")

            if article_like and body:
                cleaned = clean_text(body)
                if len(cleaned) > 120:
                    bodies.append(cleaned)

    if not bodies:
        return ""

    bodies.sort(key=len, reverse=True)
    return bodies[0]


def extract_article_text_from_next_data(page_html):
    """
    Fox pages sometimes carry useful article chunks inside script JSON.
    This scans embedded JSON-ish text for articleBody/body/text fields.
    """
    candidates = []

    for field in ["articleBody", "body", "dek", "description"]:
        pattern = rf'"{re.escape(field)}"\s*:\s*"((?:\\.|[^"\\]){{100,}})"'

        for match in re.finditer(pattern, page_html, flags=re.IGNORECASE | re.DOTALL):
            raw = match.group(1)

            try:
                decoded = bytes(raw, "utf-8").decode("unicode_escape")
            except Exception:
                decoded = raw

            cleaned = clean_text(decoded)

            if len(cleaned) > 120:
                candidates.append(cleaned)

    if not candidates:
        return ""

    candidates.sort(key=len, reverse=True)
    return candidates[0]


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
    lowered = text.lower().strip()

    if len(text) < 45:
        return False

    bad_phrases = [
        "subscribe",
        "sign up",
        "newsletter",
        "all rights reserved",
        "fox news",
        "click here",
        "download the app",
        "terms of use",
        "privacy policy",
        "advertisement",
        "this material may not be published",
        "getty images",
        "associated press",
        "reuters",
    ]

    if any(phrase in lowered for phrase in bad_phrases):
        return False

    # Article paragraphs usually have sentence punctuation.
    if not any(mark in text for mark in [".", "?", "!", "”", '"']):
        return False

    return True


def extract_article_text_from_paragraphs(page_html):
    parser = ParagraphExtractor()
    parser.feed(page_html)

    seen = set()
    paragraphs = []

    for paragraph in parser.paragraphs:
        paragraph = clean_text(paragraph)
        key = paragraph.lower()

        if key in seen:
            continue

        seen.add(key)

        if looks_like_article_paragraph(paragraph):
            paragraphs.append(paragraph)

    return " ".join(paragraphs).strip()


def is_valid_article_text(text):
    cleaned = clean_text(text)

    if len(cleaned) < 160:
        return False

    lowered = cleaned.lower()

    boilerplate_phrases = [
        "fox news channel offers its audiences",
        "as an alternative to the left-of-center offerings",
        "all rights reserved",
        "this material may not be published",
        "fox news network, llc",
        "privacy policy",
        "terms of use",
        "download the app",
        "subscribe to fox news",
    ]

    if any(phrase in lowered for phrase in boilerplate_phrases):
        return False

    # Prefer actual story copy with multiple sentences.
    sentence_marks = cleaned.count(".") + cleaned.count("?") + cleaned.count("!")
    if sentence_marks < 2:
        return False

    return True


def extract_article_text(page_html):
    methods = [
        ("json_ld_articleBody", extract_article_body_from_json_ld),
        ("embedded_json", extract_article_text_from_next_data),
        ("paragraphs", extract_article_text_from_paragraphs),
    ]

    for method_name, method in methods:
        text = method(page_html)
        text = clean_text(text)

        if is_valid_article_text(text):
            return method_name, text

    return "none", ""


def normalize_url(value):
    if isinstance(value, dict):
        value = value.get("@id") or value.get("url") or ""

    if isinstance(value, list):
        value = value[0] if value else ""

    value = str(value or "").strip()

    if not value:
        return ""

    return urljoin("https://www.foxnews.com/", value)


def extract_homepage_article_candidates(homepage_html):
    """
    Pull article candidates from the Fox homepage JSON-LD.
    This lets us skip video cards and test the next real article page.
    """
    candidates = []
    seen = set()

    for root in extract_json_ld_objects(homepage_html):
        for obj in flatten_json(root):
            if not isinstance(obj, dict):
                continue

            title = (
                obj.get("headline")
                or obj.get("name")
                or obj.get("title")
                or ""
            )
            link = normalize_url(
                obj.get("url")
                or obj.get("mainEntityOfPage")
                or obj.get("@id")
                or ""
            )

            title = clean_text(title)

            if not title or not link:
                continue

            if "foxnews.com" not in link:
                continue

            if link in seen:
                continue

            seen.add(link)
            candidates.append(
                {
                    "title": title,
                    "link": link,
                    "source": "homepage_json_ld",
                }
            )

    return candidates


def is_video_url(url):
    url = str(url or "").lower()
    return "/video/" in url or "video.foxnews.com" in url


def is_probably_article_url(url):
    raw_url = str(url or "").strip()
    lowered = raw_url.lower()

    if not lowered:
        return False

    if "foxnews.com" not in lowered:
        return False

    if is_video_url(lowered):
        return False

    parsed = urlparse(raw_url)
    path = (parsed.path or "").strip("/").lower()

    # Do not test the Fox homepage itself as an article.
    if not path:
        return False

    bad_parts = [
        "/category/",
        "/shows/",
        "/person/",
        "/tag/",
        "/watch/",
        "/login",
        "/newsletter",
    ]

    if any(part in lowered for part in bad_parts):
        return False

    # Real Fox articles usually have at least a section + slug:
    # /politics/slug, /sports/slug, /media/slug, /world/slug, etc.
    return "/" in path


def candidate_from_article(article):
    return {
        "title": getattr(article, "title", "") or "",
        "link": getattr(article, "link", "") or "",
        "source": "app_selected",
    }


def split_text_into_excerpts(text, limit=2000):
    """
    Split long/live article text into readable excerpts, each no longer than limit.
    Prefer splitting on sentence boundaries, then spaces.
    """
    text = clean_text(text)

    if not text:
        return []

    excerpts = []
    remaining = text

    while remaining:
        if len(remaining) <= limit:
            excerpts.append(remaining.strip())
            break

        chunk = remaining[:limit]

        # Prefer a sentence boundary near the end.
        split_at = max(
            chunk.rfind(". "),
            chunk.rfind("? "),
            chunk.rfind("! "),
        )

        # If no good sentence boundary, split at a space.
        if split_at < int(limit * 0.55):
            split_at = chunk.rfind(" ")

        # If still no safe split, hard split.
        if split_at <= 0:
            split_at = limit
        else:
            split_at += 1

        excerpts.append(remaining[:split_at].strip())
        remaining = remaining[split_at:].strip()

    return excerpts


class LiveUpdateHTMLParser(HTMLParser):
    """
    Pulls text out of one candidate live-update HTML block.
    Keeps headings, time labels, paragraphs, and embedded/social text.
    """
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
        if not value:
            return

        if self.capture_depth <= 0:
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

        if not looks_like_article_paragraph(part):
            continue

        parts.append(part)

    body = clean_text(" ".join(parts))

    if not body:
        return None

    lowered = body.lower()

    boilerplate_phrases = [
        "click here to download the fox news app",
        "this material may not be published",
        "all rights reserved",
        "fox news network, llc",
        "subscribe to fox news",
        "download the app",
        "privacy policy",
        "terms of use",
    ]

    if any(phrase in lowered for phrase in boilerplate_phrases):
        return None

    # Live updates can be shorter than normal article paragraphs, but they still need substance.
    if len(body) < 80:
        return None

    return {
        "time": time_text,
        "heading": heading,
        "text": body,
    }


def extract_html_blocks(pattern, page_html):
    return re.findall(pattern, page_html, flags=re.IGNORECASE | re.DOTALL)


def extract_live_update_items_from_article_tags(page_html):
    """
    Fox live blogs commonly render individual updates as repeated article/card blocks.
    This tries to extract each update as its own logical story/post.
    """
    blocks = []

    # Strongest signal: complete <article> blocks.
    blocks.extend(extract_html_blocks(r"<article\b[^>]*>.*?</article>", page_html))

    # Backup signals used by many React news pages.
    live_class_patterns = [
        r"<div\b[^>]+class=[\"'][^\"']*(?:live|update|post|article|story)[^\"']*[\"'][^>]*>.*?</div>",
        r"<section\b[^>]+class=[\"'][^\"']*(?:live|update|post|article|story)[^\"']*[\"'][^>]*>.*?</section>",
    ]

    if not blocks:
        for pattern in live_class_patterns:
            blocks.extend(extract_html_blocks(pattern, page_html))

    updates = []
    seen = set()

    for block in blocks:
        update = strip_fragment_to_live_update(block)

        if not update:
            continue

        key = clean_text(update["text"]).lower()

        if key in seen:
            continue

        seen.add(key)
        updates.append(update)

    # Avoid returning page-level article text as one fake live update.
    if len(updates) <= 1:
        return []

    return updates


def extract_live_update_items_from_json(page_html):
    """
    Fallback for pages that store live updates in embedded JSON.
    We recursively look for objects with text/body/description plus optional title/time.
    """
    updates = []
    seen = set()

    for script_match in re.finditer(r"<script[^>]*>(.*?)</script>", page_html, flags=re.IGNORECASE | re.DOTALL):
        raw_script = html.unescape(script_match.group(1)).strip()

        if not raw_script or len(raw_script) < 200:
            continue

        # Pull likely string fields without requiring the whole script to be valid JSON.
        item_patterns = [
            r'"(?:body|articleBody|description|text|content)"\s*:\s*"((?:\\.|[^"\\]){80,4000})"',
        ]

        for pattern in item_patterns:
            for match in re.finditer(pattern, raw_script, flags=re.IGNORECASE | re.DOTALL):
                raw = match.group(1)

                try:
                    decoded = bytes(raw, "utf-8").decode("unicode_escape")
                except Exception:
                    decoded = raw

                body = clean_text(decoded)

                if not body or len(body) < 80:
                    continue

                if not is_valid_article_text(body):
                    # Live-update fragments can be shorter, but still reject obvious junk.
                    lowered = body.lower()
                    if (
                        "fox news channel offers its audiences" in lowered
                        or "all rights reserved" in lowered
                        or "privacy policy" in lowered
                        or "terms of use" in lowered
                    ):
                        continue

                key = body.lower()

                if key in seen:
                    continue

                seen.add(key)
                updates.append(
                    {
                        "time": "",
                        "heading": "",
                        "text": body,
                    }
                )

    # JSON fallback can be noisy; only trust it if it found multiple distinct items.
    if len(updates) <= 1:
        return []

    return updates


def extract_live_update_items(page_html):
    updates = extract_live_update_items_from_article_tags(page_html)

    if updates:
        return updates

    return extract_live_update_items_from_json(page_html)


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

    # Safety cap only. This should not be what creates the update items.
    if len(combined) > limit:
        shortened = combined[:limit]
        split_at = max(shortened.rfind(". "), shortened.rfind("? "), shortened.rfind("! "), shortened.rfind(" "))

        if split_at > int(limit * 0.60):
            shortened = shortened[:split_at + 1]

        combined = shortened.strip() + "..."

    return combined


def main():
    forced_url = sys.argv[1].strip() if len(sys.argv) > 1 else ""

    if forced_url:
        selected = {
            "title": "Forced Fox debug URL",
            "link": forced_url,
            "source": "forced_cli_url",
        }
    else:
        selected_article = get_current_fox_article()
        selected = candidate_from_article(selected_article)

    print("\n================ FOX ARTICLE DEBUG ================")
    print(f"Fox selected headline: {selected['title']}")
    print(f"Fox selected URL: {selected['link']}")

    homepage_candidates = []

    # If the app-selected Fox headline is a video page, it probably has no article body.
    # Use the homepage JSON-LD candidates to find the next real article.
    if is_video_url(selected["link"]):
        print("Selected Fox headline is a video page; looking for the next non-video article candidate.")
        homepage_html = fetch_url_text("https://www.foxnews.com/", timeout=20)
        FOX_HOME_RAW_OUTPUT.write_text(homepage_html, encoding="utf-8")
        homepage_candidates = extract_homepage_article_candidates(homepage_html)
        print(f"Saved Fox homepage raw HTML to: {FOX_HOME_RAW_OUTPUT}")
        print(f"Found {len(homepage_candidates)} Fox homepage article candidates.")
    elif not forced_url:
        try:
            homepage_html = fetch_url_text("https://www.foxnews.com/", timeout=20)
            FOX_HOME_RAW_OUTPUT.write_text(homepage_html, encoding="utf-8")
            homepage_candidates = extract_homepage_article_candidates(homepage_html)
        except Exception as error:
            print(f"Homepage fallback candidate scan failed: {error}")

    candidates = []

    if is_probably_article_url(selected["link"]):
        candidates.append(selected)

    for candidate in homepage_candidates:
        if not is_probably_article_url(candidate.get("link", "")):
            continue

        if any(existing["link"] == candidate["link"] for existing in candidates):
            continue

        candidates.append(candidate)

    if not candidates:
        # Last-resort: test selected page even if it is a video page.
        candidates.append(selected)

    final_text = ""
    final_method = "none"
    final_candidate = None
    final_live_updates = []

    for index, candidate in enumerate(candidates, 1):
        title = candidate.get("title", "")
        link = candidate.get("link", "")

        print("\n--------------------------------------------------")
        print(f"Testing candidate {index}: {title}")
        print(f"URL: {link}")

        try:
            page_html = fetch_url_text(link, timeout=20)
        except Exception as error:
            print(f"Fetch failed for candidate {index}: {error}")
            continue

        if index == 1:
            RAW_OUTPUT.write_text(page_html, encoding="utf-8")

        raw_candidate_path = Path(f"tools/fox_article_candidate_{index}_raw.html")
        raw_candidate_path.write_text(page_html, encoding="utf-8")

        print(f"Saved raw candidate HTML to: {raw_candidate_path}")
        print(f"Raw HTML length: {len(page_html):,} characters")

        is_live_update_page = "/live-news/" in link.lower()

        if is_live_update_page:
            live_updates = extract_live_update_items(page_html)
            print(f"Live update items found: {len(live_updates)}")

            if live_updates:
                final_live_updates = live_updates
                final_text = "\n\n".join(format_live_update(item, limit=2000) for item in live_updates)
                final_method = "live_update_blocks"
                final_candidate = candidate
                break

            print("Live update block extraction failed; falling back to full-page paragraph extraction.")

        method_name, article_text = extract_article_text(page_html)
        print(f"Extraction method: {method_name}")
        print(f"Extracted text length: {len(article_text):,} characters")

        if article_text and len(article_text) > 160:
            final_text = article_text
            final_method = method_name
            final_candidate = candidate
            break

    TEXT_OUTPUT.write_text(final_text, encoding="utf-8")

    print("\n================ SELECTED ARTICLE ================")
    if final_candidate:
        print(f"Selected text source headline: {final_candidate.get('title', '')}")
        print(f"Selected text source URL: {final_candidate.get('link', '')}")
    else:
        print("Selected text source headline:")
        print("Selected text source URL:")

    print(f"Extraction method: {final_method}")
    print(f"Saved extracted Fox article text to: {TEXT_OUTPUT}")
    print(f"Extracted text length: {len(final_text):,} characters")

    selected_url = ""
    if final_candidate:
        selected_url = final_candidate.get("link", "") or ""

    is_live_update = "/live-news/" in selected_url.lower()

    print("\n================ FINAL OUTPUT ================")

    if not final_text:
        print('Fox News Article text: ""')
    elif is_live_update and final_live_updates:
        print(f"Fox News live update items: {len(final_live_updates)} total")

        for index, update in enumerate(final_live_updates, 1):
            item_text = format_live_update(update, limit=2000)
            print("")
            print(f'Fox News live update {index}: "{item_text}"')
    else:
        print(f'Fox News Article text: "{final_text}"')


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print("\n================ FINAL OUTPUT ================")
        print(f'Fox News Article text: ""')
        print(f"ERROR: {error}")
        sys.exit(1)
