import html
import re
import ssl
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass

import certifi

from services.newsmax_chrome import _close_page, _create_page, _eval, _navigate


@dataclass
class SportsArticle:
    title: str
    link: str = ""
    category: str = "ESPN"


SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())

ESPN_HOMEPAGE = "https://www.espn.com/"

ESPN_FEEDS = [
    "https://www.espn.com/espn/rss/news",
    "http://sports.espn.go.com/espn/rss/news",
]


def clean_text(value):
    if not value:
        return ""

    value = html.unescape(str(value))
    value = re.sub(r"<[^>]+>", " ", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value


def get_child_text(item, tag_name):
    for child in item:
        if child.tag.lower().endswith(tag_name.lower()):
            return clean_text(child.text or "")
    return ""


def is_valid_article(article):
    link = str(getattr(article, "link", "") or "").strip().lower()

    return bool(
        article
        and clean_text(getattr(article, "title", ""))
        and link.startswith("http")
        and (
            "/story/_/id/" in link
            or "/report/_/gameid/" in link
            or "/video/" in link
            or "/watch/" in link
        )
    )



def fetch_espn_homepage_lead():
    """
    Select ESPN's structural homepage hero lead.

    ESPN may use a normal story, match report, video, or /watch/ page for
    the lead module. The hero module itself determines priority.
    """
    target_id = ""
    ws_url = ""

    try:
        target_id, ws_url = _create_page()
        _navigate(ws_url, ESPN_HOMEPAGE)

        payload = _eval(
            ws_url,
            r"""
(() => {
    const clean = value => String(value || "")
        .replace(/\s+/g, " ")
        .trim();

    const isVisible = node => {
        if (!node) return false;

        const style = window.getComputedStyle(node);
        const rect = node.getBoundingClientRect();

        return (
            style.display !== "none"
            && style.visibility !== "hidden"
            && Number(style.opacity || 1) > 0
            && rect.width >= 80
            && rect.height >= 14
            && rect.bottom > 0
            && rect.top < window.innerHeight + 900
        );
    };

    const isEligibleHref = href => {
        const value = String(href || "").toLowerCase();

        return (
            value.includes("espn.com/")
            && (
                value.includes("/story/_/id/")
                || value.includes("/report/_/gameid/")
                || value.includes("/video/")
                || value.includes("/watch/")
            )
        );
    };

    const getHeroCandidate = hero => {
        const heading = hero.querySelector(
            "h1, h2, h3, h4, [role='heading']"
        );

        if (!heading || !isVisible(heading)) return null;

        const title = clean(heading.innerText || heading.textContent);

        if (title.length < 12) return null;

        const directLink = heading.closest("a[href]");
        const containedLink = hero.querySelector("a[href]");
        const popupNode = hero.querySelector("[data-popup-href]");

        const rawHref = (
            directLink?.href
            || containedLink?.href
            || popupNode?.getAttribute("data-popup-href")
            || ""
        );

        const href = rawHref
            ? new URL(rawHref, window.location.href).href
            : "";

        if (!isEligibleHref(href)) return null;

        const rect = hero.getBoundingClientRect();

        return {
            title,
            link: href,
            kind: "hero",
            headingTag: heading.tagName,
            headingClass: clean(heading.className || ""),
            heroClass: clean(hero.className || ""),
            top: Math.round(rect.top),
            left: Math.round(rect.left),
            width: Math.round(rect.width),
            height: Math.round(rect.height),
            score: 100000
                + Math.max(0, 3000 - Math.max(0, rect.top))
                + Math.min(
                    3000,
                    Math.round((rect.width * rect.height) / 250)
                )
        };
    };

    const heroSelectors = [
        "section.contentItem--collection.contentCollection--hero",
        "section.contentCollection--hero",
        "section.contentItem:has(.contentItem__title--hero)",
        "[class*='contentCollection--hero']",
        "[class*='contentItem--hero']"
    ];

    const heroNodes = [];
    const seenHeroes = new Set();

    for (const selector of heroSelectors) {
        for (const hero of document.querySelectorAll(selector)) {
            if (seenHeroes.has(hero)) continue;
            seenHeroes.add(hero);

            const candidate = getHeroCandidate(hero);

            if (candidate) {
                heroNodes.push(candidate);
            }
        }
    }

    heroNodes.sort((a, b) => {
        if (a.top !== b.top) return a.top - b.top;
        if (b.score !== a.score) return b.score - a.score;
        return a.left - b.left;
    });

    if (heroNodes.length) {
        return {
            selected: heroNodes[0],
            mode: "structural_hero",
            heroCandidates: heroNodes.slice(0, 8)
        };
    }

    const fallbackCandidates = [];
    const seen = new Set();

    for (const heading of document.querySelectorAll(
        "h1, h2, h3, h4, [role='heading']"
    )) {
        if (!isVisible(heading)) continue;

        const title = clean(heading.innerText || heading.textContent);

        if (title.length < 12) continue;

        const link = heading.closest("a[href]");
        const href = link ? String(link.href || "").trim() : "";

        if (!isEligibleHref(href)) continue;

        const rect = heading.getBoundingClientRect();
        const key = `${title}|${href}`;

        if (seen.has(key)) continue;
        seen.add(key);

        fallbackCandidates.push({
            title,
            link: href,
            kind: "fallback_heading",
            headingTag: heading.tagName,
            headingClass: clean(heading.className || ""),
            top: Math.round(rect.top),
            left: Math.round(rect.left),
            width: Math.round(rect.width),
            height: Math.round(rect.height),
            score: Math.max(0, 5000 - Math.max(0, rect.top))
        });
    }

    fallbackCandidates.sort((a, b) => {
        if (b.score !== a.score) return b.score - a.score;
        if (a.top !== b.top) return a.top - b.top;
        return a.left - b.left;
    });

    return {
        selected: fallbackCandidates[0] || null,
        mode: "fallback_heading",
        heroCandidates: [],
        fallbackCandidates: fallbackCandidates.slice(0, 12)
    };
})()
""",
            timeout=20,
        )

        if not isinstance(payload, dict):
            raise RuntimeError("Chrome did not return ESPN homepage data")

        selected = payload.get("selected") or {}
        title = clean_text(selected.get("title", ""))
        link = str(selected.get("link", "") or "").strip()

        if not title or not link:
            raise RuntimeError(
                "No usable ESPN homepage lead was found. "
                f"Selection mode: {payload.get('mode', 'unknown')}"
            )

        article = SportsArticle(
            title=title,
            link=link,
            category="ESPN",
        )

        print(
            "ESPN HOMEPAGE LEAD "
            f"[{payload.get('mode', 'unknown')}]: "
            f'"{article.title}"'
        )
        print(f"ESPN HOMEPAGE LEAD LINK: {article.link}")

        return article

    finally:
        if target_id:
            _close_page(target_id)


def resolve_truncated_espn_title(article):
    """
    ESPN RSS sometimes shortens headlines with "...".
    Load only those affected article pages and recover the full visible title.
    """
    original_title = clean_text(getattr(article, "title", ""))
    article_url = str(getattr(article, "link", "") or "").strip()

    if not original_title.endswith("...") or not article_url:
        return original_title

    target_id = ""
    ws_url = ""

    try:
        target_id, ws_url = _create_page()
        _navigate(ws_url, article_url)

        payload = _eval(
            ws_url,
            r"""
(() => {
    const clean = value => String(value || "")
        .replace(/\s+/g, " ")
        .replace(/\s+\|\s+ESPN$/i, "")
        .replace(/\s+-\s+ESPN$/i, "")
        .trim();

    const h1 = document.querySelector("h1");
    const ogTitle = document.querySelector('meta[property="og:title"]');
    const twitterTitle = document.querySelector('meta[name="twitter:title"]');

    return {
        h1: clean(h1 ? (h1.innerText || h1.textContent) : ""),
        ogTitle: clean(ogTitle ? ogTitle.content : ""),
        twitterTitle: clean(twitterTitle ? twitterTitle.content : ""),
        documentTitle: clean(document.title || "")
    };
})()
""",
            timeout=20,
        )

        if not isinstance(payload, dict):
            return original_title

        candidates = [
            clean_text(payload.get("h1", "")),
            clean_text(payload.get("ogTitle", "")),
            clean_text(payload.get("twitterTitle", "")),
            clean_text(payload.get("documentTitle", "")),
        ]

        for candidate in candidates:
            if len(candidate) >= 20 and not candidate.endswith("..."):
                print(
                    "EXPANDED ESPN RSS TITLE: "
                    f"{original_title} -> {candidate}"
                )
                return candidate

    except Exception as error:
        print(f"Could not expand ESPN RSS title: {original_title} -> {error}")

    finally:
        if target_id:
            _close_page(target_id)

    return original_title

def fetch_espn_sports_articles(max_articles=4):
    """
    Put ESPN's homepage lead first, then fill remaining slots from RSS.

    This preserves live-event hero items that may not appear in the RSS feed.
    """
    articles = []
    used_links = set()
    errors = []

    try:
        homepage_lead = fetch_espn_homepage_lead()

        if is_valid_article(homepage_lead):
            normalized_link = homepage_lead.link.rstrip("/").lower()
            articles.append(homepage_lead)
            used_links.add(normalized_link)

            print(
                "Loaded ESPN homepage lead first: "
                f"{homepage_lead.title}"
            )
    except Exception as error:
        message = f"homepage -> {error}"
        print(f"ESPN homepage lead fetch failed: {message}")
        errors.append(message)

    for feed_url in ESPN_FEEDS:
        try:
            print(f"Trying ESPN sports feed: {feed_url}")
            rss_articles = fetch_espn_rss(feed_url, max_articles=30)

            for article in rss_articles:
                if not is_valid_article(article):
                    continue

                normalized_link = article.link.rstrip("/").lower()

                if normalized_link in used_links:
                    continue

                article.title = resolve_truncated_espn_title(article)

                articles.append(article)
                used_links.add(normalized_link)

                if len(articles) >= max_articles:
                    print(f"Loaded ESPN Sports Desk stories: {len(articles)}")
                    return articles[:max_articles]

        except Exception as error:
            message = f"{feed_url} -> {error}"
            print(f"ESPN sports feed failed: {message}")
            errors.append(message)

    if articles:
        print(f"Loaded partial ESPN Sports Desk stories: {len(articles)}")
        return articles[:max_articles]

    print(f"All ESPN sports sources failed: {' | '.join(errors)}")
    return fallback_articles()


def fetch_espn_rss(feed_url, max_articles=20):
    request = urllib.request.Request(
        feed_url,
        headers={
            "User-Agent": "Mozilla/5.0 MorningTVUI/1.0",
            "Accept": "application/rss+xml, application/xml, text/xml, */*",
        },
    )

    with urllib.request.urlopen(
        request,
        timeout=12,
        context=SSL_CONTEXT,
    ) as response:
        xml_data = response.read()

    root = ET.fromstring(xml_data)
    items = root.findall(".//item")
    articles = []

    for item in items:
        title = get_child_text(item, "title")
        link = get_child_text(item, "link")

        if not title or not link:
            continue

        category = get_child_text(item, "category") or "ESPN"

        articles.append(
            SportsArticle(
                title=title,
                link=link,
                category=category.upper(),
            )
        )

        if len(articles) >= max_articles:
            break

    return articles


def fallback_articles():
    return [
        SportsArticle("Unable to load ESPN sports headlines.", "", "ESPN"),
        SportsArticle(
            "Check your internet connection or ESPN RSS availability.",
            "",
            "ESPN",
        ),
        SportsArticle(
            "Sports news panel will keep using fallback stories.",
            "",
            "ESPN",
        ),
        SportsArticle("Try running the app again later.", "", "ESPN"),
    ]
