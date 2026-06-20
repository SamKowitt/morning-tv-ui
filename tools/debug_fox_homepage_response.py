import sys
from pathlib import Path
from html import unescape

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from services.news_fetcher import fetch_url_text


EXPECTED = "City could be America's longest-running experiment in democratic socialism"
FOX_URL = "https://www.foxnews.com/"


def clean(value):
    return " ".join(unescape(str(value or "")).split())


def show_context(html, needle, radius=700):
    low_html = html.lower()
    low_needle = needle.lower()

    pos = low_html.find(low_needle)

    if pos < 0:
        print(f'NOT FOUND: "{needle}"')
        return

    print(f'FOUND: "{needle}"')
    print()
    print(html[max(0, pos - radius):pos + len(needle) + radius])


def main():
    print("\n================ FRESH FOX HOMEPAGE RESPONSE ================\n")

    html = fetch_url_text(FOX_URL, timeout=20)

    output = Path("tools/fox_homepage_debug_fresh.html")
    output.write_text(html, encoding="utf-8")

    print(f"Saved fresh HTML: {output}")
    print(f"Response length: {len(html):,} characters")

    title_start = html.lower().find("<title")
    title_end = html.lower().find("</title>", title_start)

    if title_start >= 0 and title_end >= 0:
        title_chunk = html[title_start:title_end + len("</title>")]
        title = clean(
            title_chunk
            .replace("<title>", "")
            .replace("</title>", "")
        )
        print(f'HTML title: "{title}"')

    print("\n---------------- EXPECTED HEADLINE ----------------")
    show_context(html, EXPECTED)

    print("\n---------------- KEY PHRASE: democratic socialism ----------------")
    show_context(html, "democratic socialism")

    print("\n---------------- KEY PHRASE: longest-running experiment ----------------")
    show_context(html, "longest-running experiment")

    print("\n---------------- CURRENT FALLBACK HEADLINE ----------------")
    show_context(
        html,
        "Trump says vandals used chemicals to sabotage his $14.8M Reflecting Pool makeover",
    )

    print("\n============================================================")


if __name__ == "__main__":
    main()
