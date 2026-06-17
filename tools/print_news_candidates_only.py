import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services import news_fetcher as nf


def candidate_get(candidate, key, default=""):
    if isinstance(candidate, dict):
        return candidate.get(key, default)
    return getattr(candidate, key, default)


def clean(value):
    try:
        return nf.clean_text(value or "")
    except Exception:
        return str(value or "").replace("\n", " ").strip()


def print_candidates(source_key, source_name, label, candidates, limit=35):
    print("")
    print("=" * 110)
    print(f"{source_key} / {source_name} — {label}")
    print(f"FOUND: {len(candidates)} candidate(s)")
    print("=" * 110)

    if not candidates:
        print("NO CANDIDATES FOUND")
        return

    for idx, candidate in enumerate(candidates[:limit], 1):
        title = clean(candidate_get(candidate, "title"))
        link = candidate_get(candidate, "link", "")
        origin = candidate_get(candidate, "origin", "") or candidate_get(candidate, "source_type", "")
        position = candidate_get(candidate, "position", "")

        print(f"{idx:02d}. {title}")
        print(f"    origin={origin} position={position}")
        print(f"    link={link}")


def try_fetch_homepage(source_key, source_name):
    print("")
    print(f"FETCHING HOMEPAGE CANDIDATES: {source_key} / {source_name}")

    funcs_to_try = [
        "fetch_homepage_candidates",
        "fetch_homepage_candidate_list",
    ]

    for func_name in funcs_to_try:
        func = getattr(nf, func_name, None)
        if not func:
            continue

        try:
            candidates = func(source_key)
            return list(candidates or [])
        except TypeError:
            pass
        except Exception:
            print(f"{func_name}({source_key}) failed:")
            traceback.print_exc()
            return []

    # Fallback: use lower-level homepage function if your file has it.
    try:
        config = nf.NEWS_SOURCES[source_key]
        homepage_url = config.get("homepage_url") or config.get("homepage")
        allowed_domain_text = config.get("allowed_domain_text") or config.get("allowed_domain") or ""

        if not homepage_url:
            print("No homepage URL configured.")
            return []

        page_html = nf.fetch_url_text(homepage_url, timeout=12)

        candidates = []

        if hasattr(nf, "extract_homepage_candidates_from_links"):
            candidates.extend(
                nf.extract_homepage_candidates_from_links(
                    page_html=page_html,
                    base_url=homepage_url,
                    allowed_domain_text=allowed_domain_text,
                )
            )

        if source_name == "CNBC" and hasattr(nf, "extract_cnbc_candidates_from_embedded_json"):
            candidates.extend(
                nf.extract_cnbc_candidates_from_embedded_json(
                    page_html=page_html,
                    base_url=homepage_url,
                )
            )

        if hasattr(nf, "extract_homepage_candidates_from_json_ld"):
            candidates.extend(
                nf.extract_homepage_candidates_from_json_ld(
                    page_html=page_html,
                    base_url=homepage_url,
                )
            )

        if hasattr(nf, "dedupe_candidates"):
            candidates = nf.dedupe_candidates(candidates)

        return list(candidates or [])

    except Exception:
        print("Homepage fallback extraction failed:")
        traceback.print_exc()
        return []


def try_fetch_rss(source_key, source_name):
    print("")
    print(f"FETCHING RSS CANDIDATES: {source_key} / {source_name}")

    func = getattr(nf, "fetch_rss_candidates", None)
    if func:
        try:
            return list(func(source_key) or [])
        except Exception:
            print(f"fetch_rss_candidates({source_key}) failed:")
            traceback.print_exc()
            return []

    print("No fetch_rss_candidates() function found.")
    return []


def main():
    sources = getattr(nf, "NEWS_SOURCES", None)
    if not sources:
        raise SystemExit("NEWS_SOURCES not found in services/news_fetcher.py")

    print("")
    print("PRINTING RAW NEWS HEADLINE CANDIDATES ONLY")
    print("This does not patch the app and does not select winners.")
    print("")

    for source_key, config in sources.items():
        source_name = config.get("source_name", source_key)

        homepage_candidates = try_fetch_homepage(source_key, source_name)
        print_candidates(source_key, source_name, "HOMEPAGE CANDIDATES", homepage_candidates)

        rss_candidates = try_fetch_rss(source_key, source_name)
        print_candidates(source_key, source_name, "RSS CANDIDATES", rss_candidates)

    print("")
    print("DONE. Tell me, for each site, which numbered HOMEPAGE candidate is the true visible top story.")
    print("If the true top story is missing from the HOMEPAGE list, then we need to scrape a different data source for that site.")


if __name__ == "__main__":
    main()
