import base64
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


def contains_meaningful_non_link_text(value):
    """
    Return True when text outside a hyperlink contains at least
    one letter or number.

    Whitespace and punctuation surrounding a standalone hyperlink
    do not make it part of an article sentence.
    """
    cleaned = clean_text(value)
    return any(character.isalnum() for character in cleaned)


class ParagraphExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_script = False
        self.in_style = False
        self.article_depth = 0
        self.in_p = False
        self.paragraph_is_in_article = False
        self.anchor_depth = 0
        self.has_link = False
        self.current = []
        self.non_link_text = []
        self.paragraphs = []
        self.article_paragraphs = []

    def _reset_paragraph(self):
        self.in_p = False
        self.paragraph_is_in_article = False
        self.anchor_depth = 0
        self.has_link = False
        self.current = []
        self.non_link_text = []

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()

        if tag == "script":
            self.in_script = True
            return

        if tag == "style":
            self.in_style = True
            return

        if self.in_script or self.in_style:
            return

        if tag == "article":
            self.article_depth += 1
            return

        if tag == "p":
            self.in_p = True
            self.paragraph_is_in_article = (
                self.article_depth > 0
            )
            self.anchor_depth = 0
            self.has_link = False
            self.current = []
            self.non_link_text = []
            return

        if tag == "a" and self.in_p:
            self.anchor_depth += 1
            self.has_link = True

    def handle_endtag(self, tag):
        tag = tag.lower()

        if tag == "script":
            self.in_script = False
            return

        if tag == "style":
            self.in_style = False
            return

        if self.in_script or self.in_style:
            return

        if tag == "a" and self.in_p:
            if self.anchor_depth > 0:
                self.anchor_depth -= 1
            return

        if tag == "p" and self.in_p:
            text = clean_text(" ".join(self.current))
            outside_link = clean_text(
                " ".join(self.non_link_text)
            )

            standalone_link_block = (
                self.has_link
                and not contains_meaningful_non_link_text(
                    outside_link
                )
            )

            if text and not standalone_link_block:
                self.paragraphs.append(text)

                if self.paragraph_is_in_article:
                    self.article_paragraphs.append(text)

            self._reset_paragraph()
            return

        if tag == "article" and self.article_depth > 0:
            self.article_depth -= 1

    def handle_data(self, data):
        if (
            not self.in_p
            or self.in_script
            or self.in_style
        ):
            return

        self.current.append(data)

        if self.anchor_depth == 0:
            self.non_link_text.append(data)

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

    source_paragraphs = (
        parser.article_paragraphs
        or parser.paragraphs
    )

    for paragraph in source_paragraphs:
        paragraph = clean_text(paragraph)
        key = paragraph.lower()

        if key in seen:
            continue

        seen.add(key)

        if looks_like_article_paragraph(paragraph):
            paragraphs.append(paragraph)

    return clean_text(" ".join(paragraphs))



def _srcset_candidates(value):
    candidates = []

    for item in str(value or "").split(","):
        item = item.strip()

        if not item:
            continue

        pieces = item.split()
        candidate_url = pieces[0].strip()
        score = 1.0

        if len(pieces) > 1:
            descriptor = pieces[-1].strip().lower()

            try:
                if descriptor.endswith("w"):
                    score = float(descriptor[:-1])
                elif descriptor.endswith("x"):
                    score = float(descriptor[:-1]) * 1000.0
            except (TypeError, ValueError):
                score = 1.0

        candidates.append((score, candidate_url))

    return candidates


def _image_candidates_from_attrs(attrs):
    values = {
        str(name or "").lower(): str(value or "").strip()
        for name, value in attrs
    }
    candidates = []

    for attribute_name in (
        "srcset",
        "data-srcset",
        "data-lazy-srcset",
    ):
        candidates.extend(
            _srcset_candidates(values.get(attribute_name, ""))
        )

    for score, attribute_name in (
        (900.0, "data-large-image"),
        (850.0, "data-image-url"),
        (800.0, "data-original"),
        (750.0, "data-lazy-src"),
        (700.0, "data-src"),
        (100.0, "src"),
    ):
        candidate_url = values.get(attribute_name, "").strip()

        if candidate_url:
            candidates.append((score, candidate_url))

    return candidates


def _usable_image_url(value, page_url):
    candidate = html.unescape(str(value or "")).strip()

    if not candidate:
        return ""

    lowered = candidate.lower()

    if (
        lowered.startswith("data:")
        or lowered.startswith("blob:")
        or "transparent" in lowered
        or "placeholder" in lowered
        or "spacer" in lowered
        or "pixel" in lowered
    ):
        return ""

    resolved = urljoin(str(page_url or ""), candidate)
    parsed = urlparse(resolved)

    if parsed.scheme not in {"http", "https"}:
        return ""

    return resolved


def _html_class_tokens(attrs):
    for name, value in attrs:
        if str(name or "").lower() != "class":
            continue

        return {
            token.lower()
            for token in str(value or "").split()
            if token
        }

    return set()


class FoxStructuredExtractor(ParagraphExtractor):
    def __init__(self):
        super().__init__()
        self.article_blocks = []

        # Preserve support for semantic figure/figcaption markup.
        self.figure_depth = 0
        self.figure_is_in_article = False
        self.figure_image_candidates = []
        self.figure_text = []
        self.figcaption_depth = 0
        self.figcaption_text = []

        # Verified Fox inline-image structure:
        #
        # div.image-ct.inline
        #   div.m
        #     picture / source / img
        #   div.info
        #     div.caption
        self.inline_image_depth = 0
        self.inline_image_is_in_article = False
        self.inline_image_candidates = []
        self.inline_info_depth = 0
        self.inline_caption_depth = 0
        self.inline_caption_text = []

    def _reset_figure(self):
        self.figure_depth = 0
        self.figure_is_in_article = False
        self.figure_image_candidates = []
        self.figure_text = []
        self.figcaption_depth = 0
        self.figcaption_text = []

    def _finish_figure(self):
        caption = clean_text(
            " ".join(self.figcaption_text)
            or " ".join(self.figure_text)
        )

        if (
            self.figure_is_in_article
            and caption
            and self.figure_image_candidates
        ):
            _score, image_url = max(
                self.figure_image_candidates,
                key=lambda item: item[0],
            )

            self.article_blocks.append({
                "type": "image",
                "text": caption,
                "image_url": image_url,
            })

        self._reset_figure()

    def _reset_inline_image(self):
        self.inline_image_depth = 0
        self.inline_image_is_in_article = False
        self.inline_image_candidates = []
        self.inline_info_depth = 0
        self.inline_caption_depth = 0
        self.inline_caption_text = []

    def _finish_inline_image(self):
        caption = clean_text(
            " ".join(self.inline_caption_text)
        )

        if (
            self.inline_image_is_in_article
            and caption
            and self.inline_image_candidates
        ):
            _score, image_url = max(
                self.inline_image_candidates,
                key=lambda item: item[0],
            )

            self.article_blocks.append({
                "type": "image",
                "text": caption,
                "image_url": image_url,
            })

        self._reset_inline_image()

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        class_tokens = _html_class_tokens(attrs)

        # Once inside a verified inline-image container, do not
        # pass its nested caption paragraph to ParagraphExtractor.
        if self.inline_image_depth > 0:
            if tag == "div":
                self.inline_image_depth += 1

                if (
                    "info" in class_tokens
                    and self.inline_info_depth == 0
                ):
                    self.inline_info_depth = (
                        self.inline_image_depth
                    )

                if (
                    "caption" in class_tokens
                    and self.inline_info_depth > 0
                    and self.inline_caption_depth == 0
                ):
                    self.inline_caption_depth = (
                        self.inline_image_depth
                    )

            if tag in {"img", "source"}:
                self.inline_image_candidates.extend(
                    _image_candidates_from_attrs(attrs)
                )

            return

        if self.figure_depth > 0:
            if tag in {"img", "source"}:
                self.figure_image_candidates.extend(
                    _image_candidates_from_attrs(attrs)
                )

            if tag == "figcaption":
                self.figcaption_depth += 1

            if tag == "figure":
                self.figure_depth += 1

            return

        if (
            tag == "div"
            and {"image-ct", "inline"}.issubset(
                class_tokens
            )
            and not self.in_script
            and not self.in_style
        ):
            self.inline_image_depth = 1
            self.inline_image_is_in_article = (
                self.article_depth > 0
            )
            self.inline_image_candidates = []
            self.inline_info_depth = 0
            self.inline_caption_depth = 0
            self.inline_caption_text = []
            return

        if (
            tag == "figure"
            and not self.in_script
            and not self.in_style
        ):
            self.figure_depth = 1
            self.figure_is_in_article = (
                self.article_depth > 0
            )
            self.figure_image_candidates = []
            self.figure_text = []
            self.figcaption_depth = 0
            self.figcaption_text = []
            return

        super().handle_starttag(tag, attrs)

    def handle_endtag(self, tag):
        tag = tag.lower()

        if self.inline_image_depth > 0:
            if tag == "div":
                if (
                    self.inline_caption_depth
                    == self.inline_image_depth
                ):
                    self.inline_caption_depth = 0

                if (
                    self.inline_info_depth
                    == self.inline_image_depth
                ):
                    self.inline_info_depth = 0

                self.inline_image_depth -= 1

                if self.inline_image_depth == 0:
                    self._finish_inline_image()

            return

        if self.figure_depth > 0:
            if (
                tag == "figcaption"
                and self.figcaption_depth > 0
            ):
                self.figcaption_depth -= 1
                return

            if tag == "figure":
                self.figure_depth -= 1

                if self.figure_depth == 0:
                    self._finish_figure()

                return

            return

        previous_count = len(self.article_paragraphs)
        super().handle_endtag(tag)

        if (
            tag == "p"
            and len(self.article_paragraphs) > previous_count
        ):
            self.article_blocks.append({
                "type": "paragraph",
                "text": self.article_paragraphs[-1],
            })

    def handle_data(self, data):
        if self.inline_image_depth > 0:
            if self.inline_caption_depth > 0:
                self.inline_caption_text.append(data)

            return

        if self.figure_depth > 0:
            self.figure_text.append(data)

            if self.figcaption_depth > 0:
                self.figcaption_text.append(data)

            return

        super().handle_data(data)

def _trim_structured_blocks_to_cleaned_text(blocks, cleaned_text):
    target = clean_text(cleaned_text)

    if not target:
        return []

    kept = []
    accumulated = ""

    for raw_block in blocks:
        block = dict(raw_block)
        block_type = str(
            block.get("type", "paragraph") or "paragraph"
        ).strip().lower()

        if block_type == "image":
            kept.append(block)
            continue

        block_text = clean_text(block.get("text", ""))

        if not block_text:
            continue

        candidate = clean_text(
            f"{accumulated} {block_text}"
        )

        if target.startswith(candidate):
            kept.append(block)
            accumulated = candidate
            continue

        if target.startswith(accumulated):
            remaining = target[len(accumulated):].strip()

            if remaining and block_text.startswith(remaining):
                block["text"] = remaining
                block.pop("html", None)
                kept.append(block)

        break

    return kept


def extract_fox_article_payload(page_html, page_url):
    parser = FoxStructuredExtractor()
    parser.feed(page_html)

    blocks = []
    seen_paragraphs = set()
    seen_images = set()

    for raw_block in parser.article_blocks:
        block_type = str(
            raw_block.get("type", "paragraph") or "paragraph"
        ).strip().lower()

        if block_type == "image":
            caption = clean_text(raw_block.get("text", ""))
            image_url = _usable_image_url(
                raw_block.get("image_url", ""),
                page_url,
            )
            image_key = (
                image_url.lower(),
                caption.lower(),
            )

            if (
                not image_url
                or not caption
                or image_key in seen_images
            ):
                continue

            seen_images.add(image_key)
            blocks.append({
                "type": "image",
                "text": caption,
                "image_url": image_url,
            })
            continue

        paragraph = clean_text(raw_block.get("text", ""))
        paragraph_key = paragraph.lower()

        if (
            not paragraph
            or paragraph_key in seen_paragraphs
            or not looks_like_article_paragraph(paragraph)
        ):
            continue

        seen_paragraphs.add(paragraph_key)
        blocks.append({
            "type": "paragraph",
            "text": paragraph,
        })

    text = clean_text(" ".join(
        block["text"]
        for block in blocks
        if block.get("type") != "image"
    ))
    cleaned_text = prepare_article_text_for_display(text)

    return {
        "text": cleaned_text,
        "blocks": _trim_structured_blocks_to_cleaned_text(
            blocks,
            cleaned_text,
        ),
    }

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


ARTICLE_END_CLEANUP_VERSION = 5

ARTICLE_END_BOILERPLATE_PATTERNS = (
    # News-tip solicitation sections.
    re.compile(
        r"\s*(?:News Tips\s*)?"
        r"Got (?:a )?(?:confidential )?news tip\?\s*"
        r"We want to hear from you\.?"
        r"(?:\s*Get this delivered to your inbox,?\s*"
        r"and more info about our products and services\.?)?"
        r"\s*$",
        flags=re.IGNORECASE,
    ),
    re.compile(
        r"\s*News Tips\s*"
        r"(?:Have|Got) (?:a )?news tip\?\s*"
        r"(?:We want to hear from you|Tell us about it)\.?\s*$",
        flags=re.IGNORECASE,
    ),
    re.compile(
        r"\s*Got (?:a )?confidential news tip\?\s*"
        r"We want to hear from you\.?\s*$",
        flags=re.IGNORECASE,
    ),

    # Social-media and reporter contact prompts.
    re.compile(
        r"\s*Follow\b.*$",
        flags=re.IGNORECASE,
    ),
    re.compile(
        r"\s*(?:"
        r"Email\s+(?:the\s+)?(?:reporter|author|writer)\s+at\s+"
        r"|Email\s+(?:news\s+)?tips\s+to\s+"
        r"|Send\s+(?:news\s+)?tips\s+to\s+"
        r")"
        r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}"
        r"(?:[.,;]?\s+(?:and\s+)?follow\b.*)?"
        r"\.?\s*$",
        flags=re.IGNORECASE,
    ),

    # CNBC-style market-data notices.
    re.compile(
        r"\s*(?:Data is a real-time snapshot\.?\s*)?"
        r"\*?\s*Data is delayed at least \d+\s+minutes\.?\s*"
        r"Global Business and Financial News, Stock Quotes, "
        r"and Market Data and Analysis\.?\s*$",
        flags=re.IGNORECASE,
    ),
    re.compile(
        r"\s*Global Business and Financial News, Stock Quotes, "
        r"and Market Data and Analysis\.?\s*$",
        flags=re.IGNORECASE,
    ),
    re.compile(
        r"\s*\*?\s*Data is delayed at least \d+\s+minutes\.?\s*$",
        flags=re.IGNORECASE,
    ),
    re.compile(
        r"\s*Data is a real-time snapshot\.?\s*$",
        flags=re.IGNORECASE,
    ),

    # Reporter/author biography paragraphs at the article's end.
    # The name portion remains case-sensitive so an ordinary sentence
    # cannot accidentally be interpreted as a reporter name.
    re.compile(
        r"\s*[A-Z][A-Za-zÀ-ÖØ-öø-ÿ’'.-]+"
        r"(?:\s+[A-Z][A-Za-zÀ-ÖØ-öø-ÿ’'.-]+){1,5}"
        r"\s+(?i:is\s+(?:an?|the)\s+[^.]{0,320}"
        r"\b(?:reporter|correspondent|editor|producer|journalist)\b"
        r"[^.]*\."
        r"(?:\s+(?:Previous(?:ly)?|Before joining|Prior to joining|"
        r"She previously|He previously|They previously|Her bylines|"
        r"His bylines|Their bylines)\b[^.]*\.){0,3})\s*$",
    ),
)

TRAILING_CONTRIBUTOR_PHRASES = (
    "contributed to this report",
    "contributed to the report",
    "contributed to this story",
    "contributed to the story",
    "contributed reporting to this report",
    "contributed reporting to the report",
    "contributed reporting to this story",
    "contributed reporting to the story",
    "contributed reporting",
)


def strip_trailing_article_boilerplate(text):
    """
    Remove publication boilerplate only from the end of an article.

    Applying these patterns at the end prevents similar wording inside
    legitimate article content from being removed.
    """
    value = clean_text(text)
    previous = None

    while value and value != previous:
        previous = value

        for pattern in ARTICLE_END_BOILERPLATE_PATTERNS:
            value = pattern.sub("", value).strip()

    return value


def separate_trailing_contributor_credit(text):
    """
    Put a final contributor credit into its own visible paragraph.
    """
    value = str(text or "").strip()

    if not value:
        return ""

    lowered = value.lower()
    phrase_position = max(
        lowered.rfind(phrase)
        for phrase in TRAILING_CONTRIBUTOR_PHRASES
    )

    if phrase_position < 0:
        return value

    # The contribution phrase must occur near the end. This avoids
    # separating an ordinary sentence elsewhere in the article.
    if len(value) - phrase_position > 220:
        return value

    # Locate the preceding sentence boundary. A period belonging to a
    # single-letter initial, such as "Devon M. Sayers", is not treated
    # as the beginning of a new sentence.
    boundaries = list(
        re.finditer(
            r"(?<!\b[A-Z])[.!?]\s+",
            value[:phrase_position],
        )
    )

    credit_start = (
        boundaries[-1].end()
        if boundaries
        else 0
    )

    credit = value[credit_start:].strip()

    if (
        not credit
        or len(credit) > 650
        or not any(
            phrase in credit.lower()
            for phrase in TRAILING_CONTRIBUTOR_PHRASES
        )
    ):
        return value

    body = value[:credit_start].strip()

    if not body:
        return credit

    return f"{body}\n\n{credit}"


def prepare_article_text_for_display(text):
    value = strip_trailing_article_boilerplate(text)
    return separate_trailing_contributor_credit(value)


def finalize_article_payload(payload):
    """
    Apply shared article-end cleanup to non-ESPN provider payloads.
    """
    if not isinstance(payload, dict):
        return payload

    result = dict(payload)
    original_text = str(result.get("text", "") or "")
    revised_text = prepare_article_text_for_display(original_text)

    result["text"] = revised_text
    result["cleanup_version"] = ARTICLE_END_CLEANUP_VERSION

    # A provider payload containing structured blocks would otherwise
    # take priority over the cleaned text in the newspaper dialog.
    if (
        result.get("blocks")
        and revised_text != original_text
    ):
        result["blocks"] = []

    return result


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




ARTICLE_IMAGE_DATA_CACHE = {}
MAX_ARTICLE_IMAGE_BYTES = 15 * 1024 * 1024
MAX_ARTICLE_IMAGE_MEMORY_ENTRIES = 24


def _download_article_image_bytes(image_url, timeout=20):
    parsed_image_url = urlparse(str(image_url or ""))
    image_referer = (
        f"{parsed_image_url.scheme}://{parsed_image_url.netloc}/"
        if parsed_image_url.scheme and parsed_image_url.netloc
        else ""
    )

    request_headers = {
        "User-Agent": USER_AGENT,
        "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
        "Cache-Control": "no-cache",
    }

    if image_referer:
        request_headers["Referer"] = image_referer

    request = urllib.request.Request(
        image_url,
        headers=request_headers,
    )

    def read_with_context(context=None):
        with urllib.request.urlopen(
            request,
            timeout=timeout,
            context=context or SSL_CONTEXT,
        ) as response:
            data = response.read(
                MAX_ARTICLE_IMAGE_BYTES + 1
            )

            if len(data) > MAX_ARTICLE_IMAGE_BYTES:
                raise RuntimeError(
                    "Article image exceeded the size limit"
                )

            return data

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
            return read_with_context(
                ssl._create_unverified_context()
            )

        raise


def _article_image_base64(image_url):
    image_url = str(image_url or "").strip()

    if not image_url:
        return ""

    cached = ARTICLE_IMAGE_DATA_CACHE.get(image_url)

    if cached:
        return cached

    image_bytes = _download_article_image_bytes(image_url)

    if len(image_bytes) < 64:
        raise RuntimeError("Article image response was empty")

    encoded = base64.b64encode(image_bytes).decode("ascii")
    ARTICLE_IMAGE_DATA_CACHE[image_url] = encoded

    while (
        len(ARTICLE_IMAGE_DATA_CACHE)
        > MAX_ARTICLE_IMAGE_MEMORY_ENTRIES
    ):
        oldest_key = next(iter(ARTICLE_IMAGE_DATA_CACHE))
        ARTICLE_IMAGE_DATA_CACHE.pop(oldest_key, None)

    return encoded


def hydrate_article_image_blocks(payload):
    if not isinstance(payload, dict):
        return payload

    result = dict(payload)
    hydrated_blocks = []

    for raw_block in result.get("blocks", []) or []:
        if not isinstance(raw_block, dict):
            continue

        block = dict(raw_block)
        block_type = str(
            block.get("type", "paragraph") or "paragraph"
        ).strip().lower()

        if block_type != "image":
            hydrated_blocks.append(block)
            continue

        image_url = str(
            block.get("image_url", "") or ""
        ).strip()

        try:
            image_data = _article_image_base64(image_url)
        except Exception as error:
            print(
                "ARTICLE IMAGE LOAD FAILED: "
                f"{image_url} -> {error}"
            )
            continue

        if not image_data:
            continue

        block["image_data"] = image_data
        hydrated_blocks.append(block)

    result["blocks"] = hydrated_blocks
    return result


def fetch_cnbc_article_payload(url):
    """
    CNBC article images and captions are available in the rendered
    ArticleBody DOM rather than in the direct urllib response.
    """
    import time as time_module

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
        _navigate(ws_url, url)

        # Wait in Python so a slow CNBC render cannot trap _eval() inside
        # a long-running asynchronous JavaScript loop.
        root_ready = False

        for _attempt in range(12):
            try:
                root_ready = bool(
                    _eval(
                        ws_url,
                        r"""
(() => {
    const root =
        document.querySelector('[data-module="ArticleBody"]') ||
        document.querySelector('[data-test^="articleBody"]') ||
        document.querySelector(".ArticleBody-articleBody");

    return Boolean(
        root &&
        root.querySelector(
            ".group p, .group h2, .group h3, "
            + ".group h4, .InlineImage-imageEmbed"
        )
    );
})()
""",
                        timeout=8,
                    )
                )
            except Exception:
                root_ready = False

            if root_ready:
                break

            time_module.sleep(0.5)

        payload = _eval(
            ws_url,
            r"""
(() => {
    const clean = value => String(value || "")
        .replace(/\s+/g, " ")
        .trim();

    const root =
        document.querySelector('[data-module="ArticleBody"]') ||
        document.querySelector('[data-test^="articleBody"]') ||
        document.querySelector(".ArticleBody-articleBody");

    if (!root) {
        return {
            error: "CNBC ArticleBody root was not found",
            pageTitle: document.title || ""
        };
    }

    const headlineNode =
        document.querySelector("h1.ArticleHeader-headline") ||
        document.querySelector("main h1") ||
        document.querySelector("h1");

    const headline = clean(
        headlineNode
            ? (
                headlineNode.innerText ||
                headlineNode.textContent
            )
            : ""
    );

    const usableText = value => {
        const text = clean(value);

        if (text.length < 20) {
            return false;
        }

        const lowered = text.toLowerCase();
        const blockedBits = [
            "create free account",
            "choose cnbc as your preferred source",
            "follow your favorite stocks",
            "advertisement",
            "privacy policy",
            "terms of service"
        ];

        if (
            blockedBits.some(
                bit => lowered.includes(bit)
            )
        ) {
            return false;
        }

        return /[.!?…”"]/.test(text);
    };

    const bestSrcsetUrl = value => {
        let bestUrl = "";
        let bestScore = -1;

        for (const item of String(value || "").split(",")) {
            const pieces = item.trim().split(/\s+/);

            if (!pieces[0]) {
                continue;
            }

            const descriptor = String(
                pieces[pieces.length - 1] || ""
            ).toLowerCase();
            let score = 1;

            if (/^[0-9.]+w$/.test(descriptor)) {
                score = Number(
                    descriptor.slice(0, -1)
                ) || 1;
            } else if (/^[0-9.]+x$/.test(descriptor)) {
                score = (
                    Number(
                        descriptor.slice(0, -1)
                    ) || 1
                ) * 1000;
            } else {
                try {
                    const candidateUrl = new URL(
                        pieces[0],
                        document.baseURI
                    );
                    score = Number(
                        candidateUrl.searchParams.get("w")
                    ) || 1;
                } catch (_error) {
                    score = 1;
                }
            }

            if (score > bestScore) {
                bestScore = score;
                bestUrl = pieces[0];
            }
        }

        return bestUrl;
    };

    const usableImageUrl = value => {
        const candidate = String(value || "").trim();

        if (!candidate) {
            return "";
        }

        const lowered = candidate.toLowerCase();

        if (
            lowered.startsWith("data:") ||
            lowered.startsWith("blob:") ||
            lowered.includes("transparent") ||
            lowered.includes("placeholder") ||
            lowered.includes("spacer") ||
            lowered.includes("pixel")
        ) {
            return "";
        }

        try {
            return new URL(
                candidate,
                document.baseURI
            ).href;
        } catch (_error) {
            return "";
        }
    };

    const imageUrlForContainer = container => {
        const image = container.querySelector("img");
        const candidates = [];

        if (image) {
            // CNBC's rendered img.src is a JPEG URL. Prefer it over
            // currentSrc, which can resolve to WebP on this Mac.
            candidates.push(
                image.getAttribute("src"),
                image.currentSrc,
                bestSrcsetUrl(
                    image.getAttribute("srcset")
                ),
                bestSrcsetUrl(
                    image.getAttribute("data-srcset")
                ),
                image.getAttribute("data-src"),
                image.getAttribute("data-lazy-src")
            );
        }

        const sourceCandidates = Array.from(
            container.querySelectorAll(
                "picture source[srcset], "
                + "source[data-srcset]"
            )
        )
            .map(source => ({
                url:
                    bestSrcsetUrl(
                        source.getAttribute("srcset")
                    ) ||
                    bestSrcsetUrl(
                        source.getAttribute(
                            "data-srcset"
                        )
                    ),
                width:
                    Number(
                        source.getAttribute("width")
                    ) || 0
            }))
            .sort(
                (left, right) =>
                    right.width - left.width
            );

        for (const source of sourceCandidates) {
            candidates.push(source.url);
        }

        for (const candidate of candidates) {
            const resolved = usableImageUrl(candidate);

            if (resolved) {
                return resolved;
            }
        }

        return "";
    };

    const captionForContainer = container => {
        const captionNode = container.querySelector(
            ".InlineImage-imageEmbedCaption"
        );
        const creditNode = container.querySelector(
            ".InlineImage-imageEmbedCredit"
        );
        const caption = clean(
            captionNode
                ? (
                    captionNode.innerText ||
                    captionNode.textContent
                )
                : ""
        );
        const credit = clean(
            creditNode
                ? (
                    creditNode.innerText ||
                    creditNode.textContent
                )
                : ""
        );

        return clean(
            [caption, credit]
                .filter(Boolean)
                .join(" ")
        );
    };

    const articleNodes = root.querySelectorAll(
        ".InlineImage-imageEmbed, "
        + ".group h2, .group h3, .group h4, "
        + ".group p, .group li, .group blockquote"
    );
    const blocks = [];
    const seenText = new Set();
    const seenImages = new Set();

    for (const node of articleNodes) {
        if (
            node.matches(
                ".InlineImage-imageEmbed"
            )
        ) {
            const imageUrl =
                imageUrlForContainer(node);
            const caption =
                captionForContainer(node);
            const imageKey = (
                imageUrl + "\n" + caption
            ).toLowerCase();

            if (
                !imageUrl ||
                !caption ||
                seenImages.has(imageKey)
            ) {
                continue;
            }

            seenImages.add(imageKey);
            blocks.push({
                type: "image",
                text: caption,
                image_url: imageUrl
            });
            continue;
        }

        const tag = String(
            node.tagName || ""
        ).toLowerCase();

        if (
            tag === "p" &&
            (
                node.closest("li") ||
                node.closest("blockquote")
            )
        ) {
            continue;
        }

        const text = clean(
            node.innerText ||
            node.textContent
        );
        const textKey = (
            tag + "\n" + text
        ).toLowerCase();
        let blockType = "paragraph";

        if (
            ["h2", "h3", "h4"].includes(tag)
        ) {
            blockType = "heading";
        } else if (tag === "li") {
            blockType = "list_item";
        } else if (tag === "blockquote") {
            blockType = "quote";
        }

        const valid = (
            blockType === "heading"
                ? (
                    text.length >= 8
                    && text.length <= 240
                )
                : usableText(text)
        );

        if (
            !valid ||
            seenText.has(textKey)
        ) {
            continue;
        }

        seenText.add(textKey);

        blocks.push({
            type: blockType,
            text
        });
    }

    const articleText = blocks
        .filter(block => block.type !== "image")
        .map(block => block.text)
        .join("\n\n")
        .trim();

    return {
        headline,
        text: articleText,
        blocks,
        paragraphCount: blocks.filter(
            block => block.type === "paragraph"
        ).length,
        imageCount: blocks.filter(
            block => block.type === "image"
        ).length,
        pageTitle: document.title || ""
    };
})()
""",
            timeout=30,
        )

        if not isinstance(payload, dict):
            raise RuntimeError(
                "Chrome did not return a CNBC article payload"
            )

        if payload.get("error"):
            raise RuntimeError(
                str(payload.get("error"))
                + f". Page title: {payload.get('pageTitle', '')!r}"
            )

        allowed_block_types = {
            "heading",
            "paragraph",
            "list_item",
            "quote",
            "image",
        }
        article_blocks = []

        for raw_block in payload.get("blocks", []) or []:
            if not isinstance(raw_block, dict):
                continue

            block_type = str(
                raw_block.get("type", "paragraph")
                or "paragraph"
            ).strip().lower()
            block_text = clean_text(
                raw_block.get("text", "")
            )

            if (
                block_type not in allowed_block_types
                or not block_text
            ):
                continue

            if block_type == "image":
                image_url = _usable_image_url(
                    raw_block.get("image_url", ""),
                    url,
                )

                if not image_url:
                    continue

                article_blocks.append({
                    "type": "image",
                    "text": block_text,
                    "image_url": image_url,
                })
                continue

            article_blocks.append({
                "type": block_type,
                "text": block_text,
            })

        article_text = "\n\n".join(
            block["text"]
            for block in article_blocks
            if block.get("type") != "image"
        ).strip()
        cleaned_text = prepare_article_text_for_display(
            article_text
        )
        article_blocks = (
            _trim_structured_blocks_to_cleaned_text(
                article_blocks,
                cleaned_text,
            )
        )

        if not is_valid_article_text(cleaned_text):
            raise RuntimeError(
                "No readable CNBC article text found. "
                f"Page title: {payload.get('pageTitle', '')!r}; "
                f"paragraphs: {payload.get('paragraphCount', 0)!r}; "
                f"images: {payload.get('imageCount', 0)!r}"
            )

        print(
            "CNBC CHROME ARTICLE TEXT: "
            f"{len(cleaned_text)} chars | "
            f"{payload.get('paragraphCount', 0)} paragraphs | "
            f"{payload.get('imageCount', 0)} images | "
            f"{len(article_blocks)} structured blocks"
        )

        return {
            "is_live": False,
            "method": "cnbc_chrome",
            "cnbc_format_version": 1,
            "cleanup_version": ARTICLE_END_CLEANUP_VERSION,
            "text": cleaned_text,
            "blocks": article_blocks,
            "updates": [],
            "headline": clean_text(
                payload.get("headline", "")
            ),
        }

    finally:
        if target_id:
            _close_page(target_id)


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
    let blocks = [];

    const usableHeading = value => {
        const text = clean(value);

        if (text.length < 8 || text.length > 240) {
            return false;
        }

        const lowered = text.toLowerCase();

        if (blockedBits.some(bit => lowered.includes(bit))) {
            return false;
        }

        return lowered !== headline.toLowerCase();
    };

    const escapeHtml = value => String(value || "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;");

    const normalizeFragment = value => {
        const raw = String(value || "")
            .replace(/^#/, "")
            .trim();

        if (!raw) {
            return "";
        }

        try {
            return decodeURIComponent(raw);
        } catch (_error) {
            return raw;
        }
    };

    const currentUrl = new URL(window.location.href);
    const currentPath = currentUrl.pathname.replace(/\/+$/, "");
    const internalFragments = new Set();

    const internalFragmentForHref = value => {
        const raw = String(value || "").trim();

        if (!raw) {
            return "";
        }

        try {
            const candidateUrl = new URL(raw, currentUrl.href);
            const candidatePath = candidateUrl.pathname.replace(/\/+$/, "");

            if (
                candidateUrl.origin !== currentUrl.origin ||
                candidatePath !== currentPath ||
                !candidateUrl.hash
            ) {
                return "";
            }

            return normalizeFragment(candidateUrl.hash);
        } catch (_error) {
            return raw.startsWith("#")
                ? normalizeFragment(raw)
                : "";
        }
    };

    const inlineHtml = node => {
        const renderChild = child => {
            if (child.nodeType === Node.TEXT_NODE) {
                return escapeHtml(
                    String(child.textContent || "")
                        .replace(/\s+/g, " ")
                );
            }

            if (child.nodeType !== Node.ELEMENT_NODE) {
                return "";
            }

            const tag = String(child.tagName || "").toLowerCase();
            const content = Array.from(child.childNodes)
                .map(renderChild)
                .join("");

            if (tag === "strong" || tag === "b") {
                return `<strong>${content}</strong>`;
            }

            if (tag === "em" || tag === "i") {
                return `<em>${content}</em>`;
            }

            if (tag === "a") {
                const linkText = escapeHtml(
                    clean(child.innerText || child.textContent || "")
                );
                const fragment = internalFragmentForHref(
                    child.getAttribute("href") || ""
                );

                if (fragment) {
                    internalFragments.add(fragment);

                    return (
                        '<a href="article-anchor:'
                        + encodeURIComponent(fragment)
                        + '" style="color:#0057b8; '
                        + 'text-decoration:none; font-weight:700;">'
                        + linkText
                        + "</a>"
                    );
                }

                // External ESPN links keep their visible words but lose
                // hyperlink styling and interaction inside the newspaper.
                return linkText;
            }

            if (tag === "br") {
                return "<br>";
            }

            return content;
        };

        return Array.from(node.childNodes)
            .map(renderChild)
            .join("")
            .trim();
    };

    const excludedContainerBits = [
        "editors-picks",
        "editor-picks",
        "editors_picks",
        "editor_picks",
        "editorspicks",
        "editorpicks",
        "related-content",
        "related-stories",
        "related_stories",
        "recommendation",
        "recommended",
        "recirculation",
        "recirc",
        "sidebar",
        "side-rail",
        "right-rail",
        "content-rail",
        "most-popular",
        "trending",
        "story-feed",
        "content-feed",
        "author-card",
        "author-bio",
        "byline",
        "newsletter",
        "promo-module"
    ];

    const excludedSectionTitles = [
        "editor's picks",
        "editors' picks",
        "editors picks",
        "related stories",
        "related content",
        "recommended",
        "you may also like",
        "more from espn",
        "more on this topic",
        "latest stories",
        "top stories"
    ];

    const elementMetadata = element => [
        element.id || "",
        element.className || "",
        element.getAttribute?.("data-testid") || "",
        element.getAttribute?.("data-module") || "",
        element.getAttribute?.("aria-label") || "",
        element.getAttribute?.("role") || ""
    ].join(" ").toLowerCase();

    const metadataIsExcluded = element => {
        const metadata = elementMetadata(element);

        return excludedContainerBits.some(
            bit => metadata.includes(bit)
        );
    };

    const firstSectionHeading = element => {
        const heading = element.querySelector?.(
            "h1, h2, h3, h4, [role='heading']"
        );

        return clean(
            heading
                ? (heading.innerText || heading.textContent)
                : ""
        ).toLowerCase();
    };

    const isExcludedNode = node => {
        const semanticContainer = node.closest(
            "aside, nav, footer, [role='complementary'], "
            + "[aria-label*='editor' i], "
            + "[aria-label*='related' i], "
            + "[aria-label*='recommended' i]"
        );

        // Verified ESPN article-photo structure:
        //
        // aside.inline.inline-photo
        //   figure
        //     picture / source / img
        //     figcaption.photoCaption
        //
        // ESPN uses an <aside> for inline editorial photos. Preserve only
        // nodes inside that exact figure while continuing to reject normal
        // sidebars, recommendations, navigation, and complementary rails.
        const verifiedInlinePhotoFigure = node.closest(
            "aside.inline.inline-photo > figure"
        );

        if (
            semanticContainer
            && !verifiedInlinePhotoFigure
        ) {
            return true;
        }

        let container = node.parentElement;

        while (container && container !== root) {
            if (metadataIsExcluded(container)) {
                return true;
            }

            const sectionHeading = firstSectionHeading(container);

            if (
                sectionHeading &&
                excludedSectionTitles.some(
                    title => sectionHeading.includes(title)
                )
            ) {
                return true;
            }

            container = container.parentElement;
        }

        return false;
    };

    const bestSrcsetUrl = value => {
        let bestUrl = "";
        let bestScore = -1;

        for (const item of String(value || "").split(",")) {
            const pieces = item.trim().split(/\s+/);

            if (!pieces[0]) {
                continue;
            }

            const descriptor = String(
                pieces[pieces.length - 1] || ""
            ).toLowerCase();
            let score = 1;

            if (/^[0-9.]+w$/.test(descriptor)) {
                score = Number(descriptor.slice(0, -1)) || 1;
            } else if (/^[0-9.]+x$/.test(descriptor)) {
                score = (
                    Number(descriptor.slice(0, -1)) || 1
                ) * 1000;
            }

            if (score >= bestScore) {
                bestScore = score;
                bestUrl = pieces[0];
            }
        }

        return bestUrl;
    };

    const usableImageUrl = value => {
        const candidate = String(value || "").trim();

        if (!candidate) {
            return "";
        }

        const lowered = candidate.toLowerCase();

        if (
            lowered.startsWith("data:") ||
            lowered.startsWith("blob:") ||
            lowered.includes("transparent") ||
            lowered.includes("placeholder") ||
            lowered.includes("spacer") ||
            lowered.includes("pixel")
        ) {
            return "";
        }

        try {
            return new URL(
                candidate,
                document.baseURI
            ).href;
        } catch (_error) {
            return "";
        }
    };

    const imageUrlForFigure = figure => {
        const image = figure.querySelector("img");
        const candidates = [];

        if (image) {
            candidates.push(
                image.currentSrc,
                bestSrcsetUrl(
                    image.getAttribute("srcset")
                ),
                bestSrcsetUrl(
                    image.getAttribute("data-srcset")
                ),
                image.getAttribute("data-large-image"),
                image.getAttribute("data-image-url"),
                image.getAttribute("data-original"),
                image.getAttribute("data-lazy-src"),
                image.getAttribute("data-src"),
                image.getAttribute("src")
            );
        }

        for (const source of figure.querySelectorAll(
            "picture source[srcset], "
            + "source[data-srcset]"
        )) {
            candidates.push(
                bestSrcsetUrl(
                    source.getAttribute("srcset")
                ),
                bestSrcsetUrl(
                    source.getAttribute("data-srcset")
                )
            );
        }

        for (const candidate of candidates) {
            const resolved = usableImageUrl(candidate);

            if (resolved) {
                return resolved;
            }
        }

        return "";
    };

    const captionForFigure = figure => {
        const captionNode =
            figure.querySelector("figcaption") ||
            figure.querySelector(
                '[class*="caption" i]'
            ) ||
            figure.querySelector(
                '[data-testid*="caption" i]'
            );
        const image = figure.querySelector("img");

        return clean(
            captionNode
                ? (
                    captionNode.innerText ||
                    captionNode.textContent
                )
                : (
                    image?.getAttribute("alt") ||
                    image?.getAttribute("title") ||
                    ""
                )
        );
    };

    const articleNodes = root.querySelectorAll(
        "h2, h3, h4, [role='heading'], "
        + "p, li, blockquote, figure"
    );
    const blockByNode = new Map();
    const seenImages = new Set();

    for (const node of articleNodes) {
        const tag = String(node.tagName || "").toLowerCase();

        if (isExcludedNode(node)) {
            continue;
        }

        if (tag === "figure") {
            const imageUrl = imageUrlForFigure(node);
            const caption = captionForFigure(node);
            const imageKey = (
                imageUrl + "\n" + caption
            ).toLowerCase();

            if (
                !imageUrl ||
                !caption ||
                seenImages.has(imageKey)
            ) {
                continue;
            }

            seenImages.add(imageKey);

            blocks.push({
                type: "image",
                text: caption,
                image_url: imageUrl
            });
            continue;
        }

        // The figure block already contains its caption.
        if (node.closest("figure")) {
            continue;
        }

        // A list item or blockquote can contain its own paragraph element.
        // Keep only the outer semantic block so text is not duplicated.
        if (
            tag === "p" &&
            (node.closest("li") || node.closest("blockquote"))
        ) {
            continue;
        }

        const text = clean(node.innerText || node.textContent);
        const key = text.toLowerCase();

        let blockType = "paragraph";

        if (
            ["h2", "h3", "h4"].includes(tag) ||
            node.getAttribute("role") === "heading"
        ) {
            blockType = "heading";
        } else if (tag === "li") {
            blockType = "list_item";
        } else if (tag === "blockquote") {
            blockType = "quote";
        }

        const hasInternalArticleLinks = Array.from(
            node.querySelectorAll("a[href]")
        ).some(link => Boolean(
            internalFragmentForHref(
                link.getAttribute("href") || ""
            )
        ));

        const valid = (
            blockType === "heading"
                ? usableHeading(text)
                : (
                    usable(text)
                    || (
                        text.length >= 8
                        && hasInternalArticleLinks
                    )
                )
        );

        if (!valid || seen.has(key)) {
            continue;
        }

        seen.add(key);

        const block = {
            type: blockType,
            text,
            html: inlineHtml(node)
        };

        blocks.push(block);
        blockByNode.set(node, block);
    }

    const normalizedAnchorValue = element => normalizeFragment(
        element?.id ||
        element?.getAttribute?.("name") ||
        ""
    ).toLowerCase();

    const findAnchorTarget = fragment => {
        const exactIdTarget = document.getElementById(fragment);

        if (exactIdTarget) {
            return exactIdTarget;
        }

        const normalizedFragment = normalizeFragment(fragment).toLowerCase();

        return Array.from(
            document.querySelectorAll("[id], [name]")
        ).find(
            element => (
                normalizedAnchorValue(element)
                === normalizedFragment
            )
        ) || null;
    };

    const includedNodes = Array.from(blockByNode.keys());

    const isIncludedHeading = node => (
        Boolean(node)
        && blockByNode.get(node)?.type === "heading"
    );

    const firstFollowingIncludedNode = (
        target,
        predicate = () => true
    ) => includedNodes.find(node => {
        if (!predicate(node)) {
            return false;
        }

        const relation = target.compareDocumentPosition(node);

        return Boolean(
            relation & Node.DOCUMENT_POSITION_FOLLOWING
        );
    }) || null;

    const destinationNodeForTarget = target => {
        if (!target) {
            return null;
        }

        // Prefer the actual subsection heading associated with an ESPN
        // fragment marker. This prevents a marker near the end of the
        // previous section from attaching to that previous paragraph.
        if (isIncludedHeading(target)) {
            return target;
        }

        const containingHeading = includedNodes.find(
            node => (
                isIncludedHeading(node)
                && node.contains(target)
            )
        );

        if (containingHeading) {
            return containingHeading;
        }

        const descendantHeading = includedNodes.find(
            node => (
                isIncludedHeading(node)
                && target.contains(node)
            )
        );

        if (descendantHeading) {
            return descendantHeading;
        }

        const followingHeading = firstFollowingIncludedNode(
            target,
            isIncludedHeading
        );

        if (followingHeading) {
            return followingHeading;
        }

        // Retain the previous generic mapping only when no associated
        // subsection heading can be found.
        if (blockByNode.has(target)) {
            return target;
        }

        const containingBlockNode = includedNodes.find(
            node => node.contains(target)
        );

        if (containingBlockNode) {
            return containingBlockNode;
        }

        const descendant = includedNodes.find(
            node => target.contains(node)
        );

        if (descendant) {
            return descendant;
        }

        return firstFollowingIncludedNode(target);
    };

    for (const fragment of internalFragments) {
        const target = findAnchorTarget(fragment);
        const destinationNode = destinationNodeForTarget(target);
        const destinationBlock = blockByNode.get(destinationNode);

        if (!destinationBlock) {
            continue;
        }

        if (!Array.isArray(destinationBlock.anchors)) {
            destinationBlock.anchors = [];
        }

        if (!destinationBlock.anchors.includes(fragment)) {
            destinationBlock.anchors.push(fragment);
        }
    }

    let articleText = blocks
        .filter(block => block.type !== "image")
        .map(block => block.text)
        .join("\n\n")
        .trim();

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
        blocks = articleLines.map(line => ({
            type: "paragraph",
            text: line
        }));

        if (articleText.length < 180 && rawText.length >= 180) {
            articleText = clean(rawText);
            blocks = [{
                type: "paragraph",
                text: articleText
            }];
        }
    }

    return {
        headline,
        text: articleText,
        blocks,
        paragraphCount: blocks.filter(
            block => block.type === "paragraph"
        ).length,
        pageTitle: document.title || ""
    };
})()
""",
            timeout=25,
        )

        if not isinstance(payload, dict):
            raise RuntimeError("Chrome did not return an ESPN article payload")

        allowed_block_types = {
            "heading",
            "paragraph",
            "list_item",
            "quote",
            "image",
        }
        article_blocks = []

        for raw_block in payload.get("blocks", []) or []:
            if not isinstance(raw_block, dict):
                continue

            block_type = str(
                raw_block.get("type", "paragraph") or "paragraph"
            ).strip().lower()
            block_text = clean_text(raw_block.get("text", ""))

            if block_type not in allowed_block_types or not block_text:
                continue

            if block_type == "image":
                image_url = _usable_image_url(
                    raw_block.get("image_url", ""),
                    url,
                )

                if not image_url:
                    continue

                article_blocks.append({
                    "type": "image",
                    "text": block_text,
                    "image_url": image_url,
                })
                continue

            article_block = {
                "type": block_type,
                "text": block_text,
            }
            block_html = str(
                raw_block.get("html", "") or ""
            ).strip()

            if block_html:
                article_block["html"] = block_html

            raw_anchors = raw_block.get("anchors", []) or []

            if isinstance(raw_anchors, str):
                raw_anchors = [raw_anchors]

            anchors = []

            for raw_anchor in raw_anchors:
                anchor = str(raw_anchor or "").strip().lstrip("#")

                if anchor and anchor not in anchors:
                    anchors.append(anchor)

            if anchors:
                article_block["anchors"] = anchors

            article_blocks.append(article_block)

        article_text = "\n\n".join(
            block["text"]
            for block in article_blocks
            if block.get("type") != "image"
        ).strip()

        if not article_text:
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
            f"{payload.get('paragraphCount', 0)} paragraphs | "
            f"{len(article_blocks)} structured blocks"
        )

        return {
            "is_live": False,
            "method": "espn_chrome",
            "format_version": 9,
            "text": article_text,
            "blocks": article_blocks,
            "updates": [],
            "headline": clean_text(payload.get("headline", "")),
        }


    finally:
        if target_id:
            _close_page(target_id)


def _fetch_article_text_payload_uncached(url):
    parsed_url = urlparse(str(url or ""))
    hostname = parsed_url.netloc.lower()

    # CNN homepage selection should never point article text at podcast,
    # audio, or Spanish landing pages. Treat those as invalid sources rather
    # than showing unrelated text inside a news story popup.
    if hostname == "cnn.com" or hostname.endswith(".cnn.com"):
        cnn_path = parsed_url.path.lower()

        blocked_cnn_paths = [
            "/audio/",
            "/podcasts/",
            "/videos/",
            "/video/",
            "/espanol/",
            "/listen/",
        ]

        if any(bit in cnn_path for bit in blocked_cnn_paths):
            raise RuntimeError(
                "CNN URL is not an English editorial article: "
                + parsed_url.path
            )

    # Newsmax must use Chrome because direct HTTP requests stall on this Mac.
    if hostname == "newsmax.com" or hostname.endswith(".newsmax.com"):
        return finalize_article_payload(
            fetch_newsmax_article_payload(url)
        )

    # ESPN serves a script/anti-bot shell to ordinary urllib requests.
    if hostname == "espn.com" or hostname.endswith(".espn.com"):
        return fetch_espn_article_payload(url)

    # CNBC's direct HTML omits the rendered inline-image structure.
    if hostname == "cnbc.com" or hostname.endswith(".cnbc.com"):
        return fetch_cnbc_article_payload(url)

    page_html = fetch_url_text(url, timeout=20)
    is_live = "/live-news/" in str(url).lower()

    if is_live:
        live_updates = extract_live_update_items_from_article_tags(page_html)

        if live_updates:
            formatted_updates = [
                format_live_update(
                    update,
                    limit=2000,
                )
                for update in live_updates
            ]

            return finalize_article_payload({
                "is_live": True,
                "method": "live_update_blocks",
                "text": "\n\n".join(formatted_updates),
                "updates": formatted_updates,
            })

    is_fox = (
        hostname == "foxnews.com"
        or hostname.endswith(".foxnews.com")
    )

    text = ""
    method = "none"

    if is_fox:
        # Preserve Fox paragraph/figure order before flattening so
        # standalone related links are removed while captioned images
        # remain paired with their captions.
        fox_payload = extract_fox_article_payload(
            page_html,
            url,
        )
        text = str(fox_payload.get("text", "") or "")
        blocks = list(fox_payload.get("blocks", []) or [])

        if is_valid_article_text(text):
            return {
                "is_live": is_live,
                "method": "fox_html_structured",
                "fox_format_version": 2,
                "cleanup_version": ARTICLE_END_CLEANUP_VERSION,
                "text": text,
                "blocks": blocks,
                "updates": [],
            }

        text = extract_article_body_from_json_ld(
            page_html
        )

        if text:
            method = "json_ld_articleBody"

    else:
        # Preserve ordinary semantic <figure> elements before
        # falling back to flattened text-only extraction.
        structured_payload = extract_fox_article_payload(
            page_html,
            url,
        )
        structured_text = str(
            structured_payload.get("text", "") or ""
        )
        structured_blocks = list(
            structured_payload.get("blocks", []) or []
        )
        has_structured_images = any(
            block.get("type") == "image"
            for block in structured_blocks
        )

        if (
            has_structured_images
            and is_valid_article_text(structured_text)
        ):
            return {
                "is_live": is_live,
                "method": "html_structured_images",
                "cleanup_version": ARTICLE_END_CLEANUP_VERSION,
                "text": structured_text,
                "blocks": structured_blocks,
                "updates": [],
            }

        text = extract_article_body_from_json_ld(
            page_html
        )

        if text:
            method = "json_ld_articleBody"
        else:
            text = extract_article_text_from_paragraphs(
                page_html
            )

            if text:
                method = "html_paragraphs"

    return finalize_article_payload({
        "is_live": is_live,
        "method": method,
        "text": text,
        "updates": [],
    })


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


def cached_article_payload_is_usable(url, payload):
    if not isinstance(payload, dict):
        return False

    if not is_valid_article_text(payload.get("text", "")):
        return False

    parsed_url = urlparse(str(url or ""))
    hostname = parsed_url.netloc.lower()
    is_espn = hostname == "espn.com" or hostname.endswith(".espn.com")
    is_cnbc = hostname == "cnbc.com" or hostname.endswith(".cnbc.com")
    is_fox = hostname == "foxnews.com" or hostname.endswith(".foxnews.com")

    if is_espn:
        try:
            format_version = int(
                payload.get("format_version", 0) or 0
            )
        except (TypeError, ValueError):
            format_version = 0

        return (
            format_version >= 9
            and bool(payload.get("blocks"))
        )

    if is_cnbc:
        try:
            cnbc_format_version = int(
                payload.get("cnbc_format_version", 0) or 0
            )
            cleanup_version = int(
                payload.get("cleanup_version", 0) or 0
            )
        except (TypeError, ValueError):
            return False

        return (
            cnbc_format_version >= 1
            and bool(payload.get("blocks"))
            and cleanup_version >= ARTICLE_END_CLEANUP_VERSION
        )

    if is_fox:
        try:
            fox_format_version = int(
                payload.get("fox_format_version", 0) or 0
            )
            cleanup_version = int(
                payload.get("cleanup_version", 0) or 0
            )
        except (TypeError, ValueError):
            return False

        return (
            fox_format_version >= 2
            and bool(payload.get("blocks"))
            and cleanup_version >= ARTICLE_END_CLEANUP_VERSION
        )

    try:
        cleanup_version = int(
            payload.get("cleanup_version", 0) or 0
        )
    except (TypeError, ValueError):
        cleanup_version = 0

    return cleanup_version >= ARTICLE_END_CLEANUP_VERSION


def fetch_article_text_payload(url):
    url = str(url or "").strip()

    cached = get_cached_article_text_payload(url)
    if cached_article_payload_is_usable(url, cached):
        print(f"ARTICLE TEXT CACHE HIT: {url}")
        return hydrate_article_image_blocks(cached)

    with ARTICLE_TEXT_PREFETCH_EVENTS_LOCK:
        event = ARTICLE_TEXT_PREFETCH_EVENTS.get(url)

    # A background preload is already working on this exact article.
    # Wait for that one instead of opening a duplicate Chrome page.
    if event is not None:
        print(f"ARTICLE TEXT WAITING FOR PRELOAD: {url}")
        event.wait(timeout=25)

        cached = get_cached_article_text_payload(url)
        if cached_article_payload_is_usable(url, cached):
            print(f"ARTICLE TEXT CACHE HIT AFTER PRELOAD: {url}")
            return hydrate_article_image_blocks(cached)

    payload = _fetch_article_text_payload_uncached(url)
    _store_cached_article_text_payload(url, payload)
    return hydrate_article_image_blocks(payload)


def prefetch_article_text_payload(url):
    url = str(url or "").strip()

    if not url:
        return

    cached = get_cached_article_text_payload(url)

    if cached_article_payload_is_usable(url, cached):
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

            if cached_article_payload_is_usable(url, cached):
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
