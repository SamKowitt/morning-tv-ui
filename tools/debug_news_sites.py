import os
import sys
import traceback
from pathlib import Path

# Make sure project root is importable when running from tools/
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Force fresh fetches instead of stale cache if your fetcher respects cache files.
for cache_name in [
    ".morning_tv_ui_news_cache.json",
    "morning_tv_ui_news_cache.json",
    ".news_cache.json",
]:
    cache_path = Path.home() / cache_name
    if cache_path.exists():
        try:
            cache_path.unlink()
            print(f"Deleted cache: {cache_path}")
        except Exception as exc:
            print(f"Could not delete cache {cache_path}: {exc}")

from services import news_fetcher as nf


def get_value(article, name, default=""):
    if isinstance(article, dict):
        return article.get(name, default)
    return getattr(article, name, default)


def print_article_result(source_key, article):
    print("")
    print("=" * 90)
    print(f"SOURCE KEY: {source_key}")
    print(f"RETURNED SOURCE: {get_value(article, 'source')}")
    print(f"RETURNED HEADLINE: {get_value(article, 'title')}")
    print(f"RETURNED LINK: {get_value(article, 'link')}")
    print(f"RETURNED IMAGE: {get_value(article, 'image_url')}")
    print("=" * 90)


def main():
    sources = getattr(nf, "NEWS_SOURCES", None)

    if not sources:
        raise SystemExit("Could not find NEWS_SOURCES in services/news_fetcher.py")

    print("")
    print("Configured news site options:")
    for key, config in sources.items():
        print(f"- {key}: {config.get('source_name', key)}")

    print("")
    print("Fetching each configured site using the same news_fetcher return path...")
    print("")

    for source_key in sources.keys():
        try:
            if hasattr(nf, "fetch_configured_article"):
                article = nf.fetch_configured_article(source_key)
            elif hasattr(nf, "fetch_article"):
                article = nf.fetch_article(source_key)
            elif hasattr(nf, "fetch_news_article"):
                article = nf.fetch_news_article(source_key)
            else:
                raise RuntimeError(
                    "No supported fetch function found. Expected one of: "
                    "fetch_configured_article, fetch_article, fetch_news_article"
                )

            print_article_result(source_key, article)

        except Exception:
            print("")
            print("=" * 90)
            print(f"SOURCE KEY: {source_key}")
            print("ERROR FETCHING SOURCE")
            traceback.print_exc()
            print("=" * 90)


if __name__ == "__main__":
    main()
