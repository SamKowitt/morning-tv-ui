import inspect
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from services import news_fetcher


EXPECTED = "City could be America's longest-running experiment in democratic socialism"


def main():
    print("\n================ FOX HEADLINE DEBUG ================\n")
    print(f'Expected Fox headline: "{EXPECTED}"\n')

    candidates = [
        name for name in dir(news_fetcher)
        if "fox" in name.lower() and callable(getattr(news_fetcher, name))
    ]

    print("Fox-related functions found:")
    for name in candidates:
        print(f"  - {name}")

    fetch_name = "fetch_fox_homepage_lead_article"

    if not hasattr(news_fetcher, fetch_name):
        print(f"\nERROR: {fetch_name} does not exist in services/news_fetcher.py")
        sys.exit(1)

    fetcher = getattr(news_fetcher, fetch_name)

    print(f"\nUsing function: {fetch_name}\n")
    print("---------------- FUNCTION SOURCE ----------------")
    print(inspect.getsource(fetcher))
    print("-------------------------------------------------\n")

    result = fetcher()

    print("================ FINAL OUTPUT ================")
    print(f"Raw result: {result!r}")

    title = getattr(result, "title", "")
    url = getattr(result, "link", "")

    if isinstance(result, dict):
        title = result.get("title", title)
        url = result.get("link", result.get("url", url))

    print(f'Fox selected headline: "{title}"')
    print(f'Fox selected URL: "{url}"')
    print(
        "Fox expected headline match: "
        + ("YES" if title.strip() == EXPECTED else "NO")
    )

    raw_path = Path("tools/fox_homepage_raw.html")
    if raw_path.exists():
        html = raw_path.read_text(encoding="utf-8", errors="ignore")
        print("\n================ EXPECTED TITLE IN RAW HTML ================")
        print("YES" if EXPECTED.lower() in html.lower() else "NO")

        if EXPECTED.lower() in html.lower():
            pos = html.lower().find(EXPECTED.lower())
            print("\nContext around expected title:\n")
            print(html[max(0, pos - 700):pos + len(EXPECTED) + 900])

    print("\n================================================")

if __name__ == "__main__":
    main()
