import contextlib
import io
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services import news_fetcher as nf


def get_value(obj, key, default=""):
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def clean(value):
    try:
        return nf.clean_text(value or "")
    except Exception:
        return str(value or "").replace("\n", " ").strip()


def quiet_fetch(source_key):
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        return nf.fetch_configured_article(source_key)


def main():
    sources = getattr(nf, "NEWS_SOURCES", {})
    if not sources:
        raise SystemExit("NEWS_SOURCES not found in services/news_fetcher.py")

    for source_key, config in sources.items():
        source_name = config.get("source_name", source_key)

        try:
            article = quiet_fetch(source_key)
            headline = clean(get_value(article, "title", ""))
            print(f'{source_name}: "{headline}"')
        except Exception as exc:
            print(f'{source_name}: "ERROR: {exc}"')


if __name__ == "__main__":
    main()
