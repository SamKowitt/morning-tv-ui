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
    return bool(
        article
        and clean_text(article.title)
        and str(article.link or "").startswith("http")
    )



def fetch_espn_homepage_lead():
    """
    Select ESPN's actual overall homepage lead sports story.

    Only real ESPN story URLs are eligible. Schedule, scores, standings,
    team pages, and other navigation links are excluded.
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

    const badTitleBits = [
        "schedule",
        "scores",
        "standings",
        "teams",
        "fixtures",
        "watch",
        "listen",
        "menu",
        "search"
    ];

    const links = Array.from(
        document.querySelectorAll('a[href*="/story/_/id/"]')
    );

    const candidates = [];

    for (const link of links) {
        const href = String(link.href || "").trim();

        if (
            !href.includes("espn.com/") ||
            !href.includes("/story/_/id/")
        ) {
            continue;
        }

        const headingNode = link.querySelector("h1, h2, h3, h4");
        const title = clean(
            headingNode
                ? (headingNode.innerText || headingNode.textContent)
                : (link.innerText || link.textContent)
        );

        const titleLower = title.toLowerCase();

        if (
            title.length < 18 ||
            badTitleBits.some(bit => titleLower === bit || titleLower.startsWith(bit))
        ) {
            continue;
        }

        const rect = link.getBoundingClientRect();

        if (rect.width < 80 || rect.height < 15) {
            continue;
        }

        const hasHeading = Boolean(headingNode);
        const hasImage = Boolean(link.querySelector("img"));

        let score = 0;
        if (hasHeading) score += 500;
        if (hasImage) score += 200;

        score += Math.max(0, 500 - Math.max(0, rect.top));
        score += Math.max(0, 250 - Math.max(0, rect.left));

        candidates.push({
            title,
            link: href,
            score,
            top: rect.top,
            left: rect.left
        });
    }

    candidates.sort((a, b) => b.score - a.score);

    return {
        count: candidates.length,
        selected: candidates[0] || null,
        topCandidates: candidates.slice(0, 12)
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

        if not title or not link or "/story/_/id/" not in link:
            raise RuntimeError(
                "No usable ESPN homepage story lead was found. "
                f"Story candidates seen: {payload.get('count', 0)}"
            )

        article = SportsArticle(
            title=title,
            link=link,
            category="ESPN",
        )

        print(f'ESPN HOMEPAGE LEAD: "{article.title}"')
        print(f"ESPN HOMEPAGE LEAD LINK: {article.link}")

        return article

    finally:
        if target_id:
            _close_page(target_id)


def fetch_espn_sports_articles(max_articles=4):
    """
    Sports Desk uses ESPN RSS story entries only.

    No homepage scraping: ESPN's homepage mixes editorial articles with
    schedule links, scoreboards, navigation, and promotional modules.
    """
    articles = []
    used_links = set()
    errors = []

    for feed_url in ESPN_FEEDS:
        try:
            print(f"Trying ESPN sports feed: {feed_url}")
            rss_articles = fetch_espn_rss(feed_url, max_articles=30)

            for article in rss_articles:
                if not is_valid_article(article):
                    continue

                normalized_link = article.link.rstrip("/").lower()

                # ESPN schedule/navigation pages are never valid Sports Desk stories.
                if "/story/_/id/" not in normalized_link:
                    print(
                        "Skipping non-story ESPN feed entry: "
                        f"{article.title} -> {article.link}"
                    )
                    continue

                if normalized_link in used_links:
                    continue

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
