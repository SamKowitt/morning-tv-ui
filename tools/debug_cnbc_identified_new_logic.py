import json
import re
import ssl
import urllib.request
from html import unescape
from pathlib import Path

RAW_PATH = Path("tools/cnbc_homepage_raw.html")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


def clean(value):
    value = unescape(str(value or ""))
    try:
        value = value.encode("utf-8").decode("unicode_escape", errors="ignore")
    except Exception:
        pass
    value = re.sub(r"<[^>]+>", " ", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def fetch_url(url):
    req = urllib.request.Request(url, headers=HEADERS)
    ctx = ssl._create_unverified_context()
    with urllib.request.urlopen(req, timeout=20, context=ctx) as resp:
        return resp.read().decode("utf-8", errors="replace")


def extract_balanced_object(source, start_index):
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


def load_s_data(html):
    marker = "window.__s_data="
    marker_index = html.find(marker)

    if marker_index < 0:
        raise RuntimeError("window.__s_data not found")

    raw_json = extract_balanced_object(html, marker_index + len(marker))

    if not raw_json:
        raise RuntimeError("Could not extract balanced window.__s_data JSON object")

    return json.loads(raw_json)


def walk(obj):
    if isinstance(obj, dict):
        yield obj
        for value in obj.values():
            yield from walk(value)
    elif isinstance(obj, list):
        for item in obj:
            yield from walk(item)


def best_title(node):
    return clean(
        node.get("headline")
        or node.get("title")
        or node.get("shorterHeadline")
        or node.get("linkHeadline")
        or node.get("promoTitle")
        or ""
    )


def best_url(node):
    url = node.get("url") or node.get("href") or node.get("liveURL") or ""
    url = str(url or "")

    if url.startswith("/"):
        url = "https://www.cnbc.com" + url

    return url.replace("\\/", "/")


def is_article_url(url):
    return bool(re.search(r"https://www\.cnbc\.com/20\d{2}/\d{2}/\d{2}/.+\.html$", url))


def should_skip_homepage_candidate(module_name, node, title, url):
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
        return True, "blank/too-short title"

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
        return True, f"skip module {module_name}"

    if "stock-market-today-live-updates" in url_l:
        return True, "skip stock market live banner URL"

    if node.get("premium") is True:
        return True, "skip premium article"

    if "/pro/" in url_l or "cnbc-pro" in section_text:
        return True, "skip CNBC Pro article"

    if "investing club" in section_text:
        return True, "skip Investing Club"

    if title_l.startswith("pro:"):
        return True, "skip Pro title"

    return False, "selected"


def select_homepage_featured_story(data):
    layouts = (
        data.get("page", {})
        .get("page", {})
        .get("layout", [])
    )

    checked = []
    position = 0
    seen = set()

    for layout_index, layout in enumerate(layouts, 1):
        for column_index, column in enumerate(layout.get("columns", []) or [], 1):
            for module_index, module in enumerate(column.get("modules", []) or [], 1):
                module_name = module.get("name", "")
                module_data = module.get("data", {})

                for node in walk(module_data):
                    url = best_url(node)
                    title = best_title(node)

                    if not is_article_url(url):
                        continue

                    key = (url, title)
                    if key in seen:
                        continue
                    seen.add(key)

                    position += 1

                    skip, reason = should_skip_homepage_candidate(module_name, node, title, url)

                    item = {
                        "position": position,
                        "layout": layout_index,
                        "column": column_index,
                        "module_index": module_index,
                        "module": module_name,
                        "type": str(node.get("type", "") or node.get("__typename", "")),
                        "premium": node.get("premium"),
                        "title": title,
                        "url": url,
                        "skip": skip,
                        "reason": reason,
                        "node": node,
                    }

                    checked.append(item)

                    if not skip:
                        return item, checked

    return None, checked


def extract_live_update_headline(article_html):
    candidates = []

    # Parse obvious JSON fields from the live-story article page.
    field_re = re.compile(
        r'"(?:headline|title|shorterHeadline|linkHeadline|promoTitle)"\s*:\s*"([^"]{20,300})"'
    )

    for match in field_re.finditer(article_html):
        title = clean(match.group(1))
        if not title:
            continue

        title_l = title.lower()

        # Structure/title filters only. Not matching any user-provided expected text.
        if any(bad in title_l for bad in [
            "cnbc",
            "watch:",
            "squawk",
            "subscribe",
            "newsletter",
            "live updates",
            "what to watch ahead",
            "top news and analysis",
            "stock market today",
        ]):
            continue

        if title not in candidates:
            candidates.append(title)

    # Prefer the first good live-update/article headline in article-page order.
    return candidates[0] if candidates else ""


def main():
    homepage_html = RAW_PATH.read_text(encoding="utf-8", errors="replace")
    homepage_data = load_s_data(homepage_html)

    selected_homepage, checked = select_homepage_featured_story(homepage_data)

    print("")
    print("CNBC HOMEPAGE MODULE CANDIDATES CHECKED")
    print("=" * 100)

    for item in checked[:40]:
        status = "SKIP" if item["skip"] else "SELECT"
        print(f'{item["position"]:02d}. {status}: "{item["title"]}"')
        print(
            f'    module: {item["module"]} | layout: {item["layout"]} | '
            f'column: {item["column"]} | module_index: {item["module_index"]}'
        )
        print(f'    type: {item["type"]} | premium: {item["premium"]}')
        print(f'    reason: {item["reason"]}')
        print(f'    url: {item["url"]}')

        if not item["skip"]:
            break

    final_title = ""
    final_url = ""
    final_source = ""

    if selected_homepage:
        homepage_title = selected_homepage["title"]
        homepage_url = selected_homepage["url"]
        homepage_type = selected_homepage["type"].lower()

        if homepage_type == "live_story" or "live" in homepage_url.lower():
            print("")
            print("CNBC selected homepage story is a live story.")
            print(f'Homepage wrapper title: "{homepage_title}"')
            print(f"Opening live story page: {homepage_url}")

            try:
                article_html = fetch_url(homepage_url)
                live_title = extract_live_update_headline(article_html)

                if live_title:
                    final_title = live_title
                    final_url = homepage_url
                    final_source = "live story page latest headline"
                else:
                    final_title = homepage_title
                    final_url = homepage_url
                    final_source = "homepage featuredNewsHero wrapper title"
            except Exception as error:
                final_title = homepage_title
                final_url = homepage_url
                final_source = f"homepage featuredNewsHero wrapper title; live page fetch failed: {error}"
        else:
            final_title = homepage_title
            final_url = homepage_url
            final_source = "homepage featured article"
    else:
        final_title = "ERROR: no usable CNBC candidate found"
        final_url = ""
        final_source = "none"

    print("")
    print("=" * 100)
    print(f'1. CNBC: "{final_title}"')
    print(f"URL: {final_url}")
    print(f"SOURCE: {final_source}")
    print("=" * 100)


if __name__ == "__main__":
    main()
