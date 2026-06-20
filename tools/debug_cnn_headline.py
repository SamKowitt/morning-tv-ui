import html
import json
import re
import ssl
import sys
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urljoin, urlparse


RAW_OUTPUT = Path("tools/cnn_homepage_raw.html")
EXPECTED_TITLE = "Tougher talks lie ahead after initial US-Iran agreement"

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125.0 Safari/537.36"
)


@dataclass
class Candidate:
    title: str
    link: str
    origin: str
    score: float


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
            "CERTIFICATE_VERIFY_FAILED" in error_text
            or "CERTIFICATE_VERIFY_FAILED" in reason_text
            or "certificate verify failed" in error_text.lower()
            or "certificate verify failed" in reason_text.lower()
        ):
            print("SSL verification failed; retrying with relaxed SSL context.")
            return read_with_context(ssl._create_unverified_context())

        raise


def import_news_fetcher_module():
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


def get_app_selected_cnn_article():
    module = import_news_fetcher_module()

    for name, args in [
        ("fetch_configured_article", ("CNN",)),
        ("fetch_cnn_article", ()),
        ("fetch_cnn_homepage_article", ()),
    ]:
        func = getattr(module, name, None)

        if not func:
            continue

        try:
            return func(*args)
        except Exception as error:
            print(f"{name}{args} failed: {error}")

    return None


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


def normalize_url(value):
    if isinstance(value, dict):
        value = value.get("@id") or value.get("url") or ""

    if isinstance(value, list):
        value = value[0] if value else ""

    value = str(value or "").strip()

    if not value:
        return ""

    return urljoin("https://www.cnn.com/", value)


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


def add_candidate(candidates, seen, title, link, origin):
    title = clean_text(title)
    link = normalize_url(link)

    if not title or not link:
        return

    if "cnn.com" not in link:
        return

    # Ignore section/homepage links.
    parsed = urlparse(link)
    path = (parsed.path or "").strip("/")

    if not path:
        return

    key = (title.lower(), link)

    if key in seen:
        return

    seen.add(key)
    candidates.append(Candidate(title=title, link=link, origin=origin, score=0.0))


def extract_from_json_ld(page_html, candidates, seen):
    for root in extract_json_ld_objects(page_html):
        for obj in flatten_json(root):
            if not isinstance(obj, dict):
                continue

            title = obj.get("headline") or obj.get("name") or obj.get("title") or ""
            link = obj.get("url") or obj.get("mainEntityOfPage") or obj.get("@id") or ""

            add_candidate(candidates, seen, title, link, "json_ld")


def extract_from_embedded_json_fields(page_html, candidates, seen):
    # Generic title/url pairs inside CNN's embedded app JSON.
    title_fields = [
        "headline",
        "title",
        "name",
        "shortTitle",
    ]

    url_fields = [
        "url",
        "uri",
        "canonicalUrl",
        "canonical_url",
        "webUrl",
        "web_url",
    ]

    # Look around the expected headline first, then scan all script text.
    scripts = re.findall(
        r"<script[^>]*>(.*?)</script>",
        page_html,
        flags=re.IGNORECASE | re.DOTALL,
    )

    for script in scripts:
        if "cnn" not in script.lower() and EXPECTED_TITLE.lower() not in script.lower():
            continue

        # First: exact expected title nearby.
        if EXPECTED_TITLE.lower() in script.lower():
            window = script[max(0, script.lower().find(EXPECTED_TITLE.lower()) - 5000): script.lower().find(EXPECTED_TITLE.lower()) + 5000]

            url_matches = re.findall(
                r'"(?:url|uri|canonicalUrl|webUrl)"\s*:\s*"([^"]+)"',
                window,
                flags=re.IGNORECASE,
            )

            for url in url_matches:
                add_candidate(candidates, seen, EXPECTED_TITLE, url, "embedded_json_expected_window")

        # Second: general title/url matching in nearby JSON.
        for title_field in title_fields:
            for match in re.finditer(
                rf'"{title_field}"\s*:\s*"((?:\\.|[^"\\]){{12,180}})"',
                script,
                flags=re.IGNORECASE | re.DOTALL,
            ):
                raw_title = match.group(1)

                try:
                    decoded_title = bytes(raw_title, "utf-8").decode("unicode_escape")
                except Exception:
                    decoded_title = raw_title

                title = clean_text(decoded_title)

                if len(title) < 12:
                    continue

                start = max(0, match.start() - 2500)
                end = min(len(script), match.end() + 2500)
                window = script[start:end]

                for url_field in url_fields:
                    for url_match in re.finditer(
                        rf'"{url_field}"\s*:\s*"([^"]+)"',
                        window,
                        flags=re.IGNORECASE,
                    ):
                        url = url_match.group(1)

                        try:
                            decoded_url = bytes(url, "utf-8").decode("unicode_escape")
                        except Exception:
                            decoded_url = url

                        add_candidate(candidates, seen, title, decoded_url, "embedded_json")


def extract_from_anchor_tags(page_html, candidates, seen):
    for match in re.finditer(
        r'<a\b[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',
        page_html,
        flags=re.IGNORECASE | re.DOTALL,
    ):
        href = match.group(1)
        inner = match.group(2)

        title = clean_text(inner)

        if len(title) < 12:
            continue

        add_candidate(candidates, seen, title, href, "anchor")


def score_candidate(candidate):
    title = candidate.title.lower()
    link = candidate.link.lower()
    expected = EXPECTED_TITLE.lower()

    score = 0.0

    if title == expected:
        score += 10000

    if expected in title:
        score += 8000

    expected_words = [word for word in re.findall(r"[a-z0-9]+", expected) if len(word) > 2]
    title_words = set(re.findall(r"[a-z0-9]+", title))

    matches = sum(1 for word in expected_words if word in title_words)
    score += matches * 120

    if "/video/" in link or "/videos/" in link or "/audio/" in link:
        score -= 2500

    if re.search(r"\b\d+:\d{2}\b", candidate.title):
        score -= 1500

    if "/2026/" in link:
        score += 200

    if "/politics/" in link or "/world/" in link or "/middleeast/" in link:
        score += 250

    if candidate.origin == "embedded_json_expected_window":
        score += 600

    if candidate.origin == "json_ld":
        score += 300

    if candidate.origin == "embedded_json":
        score += 200

    return score


def main():
    print("\n================ CNN HEADLINE DEBUG ================")
    print(f'Expected CNN headline: "{EXPECTED_TITLE}"')

    selected = get_app_selected_cnn_article()

    if selected:
        selected_title = getattr(selected, "title", "") or ""
        selected_link = getattr(selected, "link", "") or ""
        print("\nCurrent app-selected CNN article:")
        print(f"  title={selected_title}")
        print(f"  link={selected_link}")
    else:
        print("\nCurrent app-selected CNN article: NONE")

    homepage_url = "https://www.cnn.com/"
    print(f"\nFetching CNN homepage: {homepage_url}")

    page_html = fetch_url_text(homepage_url)
    RAW_OUTPUT.write_text(page_html, encoding="utf-8")

    print(f"Saved raw CNN homepage HTML to: {RAW_OUTPUT}")
    print(f"Raw HTML length: {len(page_html):,} characters")

    candidates = []
    seen = set()

    extract_from_json_ld(page_html, candidates, seen)
    extract_from_embedded_json_fields(page_html, candidates, seen)
    extract_from_anchor_tags(page_html, candidates, seen)

    for candidate in candidates:
        candidate.score = score_candidate(candidate)

    candidates.sort(key=lambda item: item.score, reverse=True)

    print("\n===== CNN homepage candidates =====")
    print("Expected:")
    print(f'  "{EXPECTED_TITLE}"')

    for index, candidate in enumerate(candidates[:20], 1):
        print(f"{index}. score={candidate.score:.1f} origin={candidate.origin} title={candidate.title}")
        print(f"   link={candidate.link}")

    best = candidates[0] if candidates else None

    print("\n================ FINAL OUTPUT ================")

    if best:
        print(f'CNN selected headline: "{best.title}"')
        print(f'CNN selected URL: "{best.link}"')

        if best.title.lower() == EXPECTED_TITLE.lower() or EXPECTED_TITLE.lower() in best.title.lower():
            print("CNN expected headline match: YES")
        else:
            print("CNN expected headline match: NO")
    else:
        print('CNN selected headline: ""')
        print('CNN selected URL: ""')
        print("CNN expected headline match: NO")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print("\n================ FINAL OUTPUT ================")
        print('CNN selected headline: ""')
        print('CNN selected URL: ""')
        print("CNN expected headline match: NO")
        print(f"ERROR: {error}")
        sys.exit(1)
