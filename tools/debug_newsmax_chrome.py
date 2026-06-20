import json
import re
import sys
import time
import urllib.request
from pathlib import Path
from urllib.parse import urljoin

from websocket import create_connection

DEBUG_URL = "http://127.0.0.1:9222/json"

HOME_URL = "https://www.newsmax.com/"
HOME_HTML_OUT = Path("tools/newsmax_from_chrome.html")
ARTICLE_HTML_OUT = Path("tools/newsmax_article_from_chrome.html")
ARTICLE_TEXT_OUT = Path("tools/newsmax_article_text.txt")


def clean(value):
    value = str(value or "")
    value = re.sub(r"\s+", " ", value).strip()
    value = re.sub(r"\s+\[?Full Story\]?\s*$", "", value, flags=re.I).strip()
    value = re.sub(r"\s+\|\s+Newsmax$", "", value, flags=re.I).strip()
    return value


def get_tabs():
    with urllib.request.urlopen(DEBUG_URL, timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))


def choose_newsmax_tab(tabs):
    for tab in tabs:
        url = str(tab.get("url", ""))
        if "newsmax.com" in url.lower() and tab.get("type") == "page":
            return tab
    return None


def cdp_eval(ws_url, expression):
    ws = create_connection(ws_url, timeout=20, origin="http://127.0.0.1:9222")

    try:
        request = {
            "id": 1,
            "method": "Runtime.evaluate",
            "params": {
                "expression": expression,
                "returnByValue": True,
                "awaitPromise": True,
            },
        }

        ws.send(json.dumps(request))

        while True:
            message = json.loads(ws.recv())

            if message.get("id") == 1:
                result = message.get("result", {}).get("result", {})
                return result.get("value", "")
    finally:
        ws.close()


def cdp_navigate(ws_url, url):
    ws = create_connection(ws_url, timeout=20, origin="http://127.0.0.1:9222")

    try:
        ws.send(json.dumps({
            "id": 1,
            "method": "Page.enable",
        }))

        ws.send(json.dumps({
            "id": 2,
            "method": "Page.navigate",
            "params": {"url": url},
        }))

        deadline = time.time() + 25
        loaded = False

        while time.time() < deadline:
            message = json.loads(ws.recv())

            if message.get("method") == "Page.loadEventFired":
                loaded = True
                break

        if not loaded:
            print("Warning: article navigation did not send loadEventFired before timeout")

    finally:
        ws.close()


def is_article_url(url):
    low = url.lower()

    if "newsmax.com/" not in low:
        return False

    blocked = [
        "/video/",
        "/videos/",
        "/tv/",
        "/podcasts/",
        "/health/",
        "/money/",
        "/books/",
        "/bestlists/",
        "/subscribe",
        "/login",
        "/about",
        "/contact",
        "/privacy",
        "/terms",
        "/advertise",
        "/newsfront/$",
    ]

    if any(bit in low for bit in blocked):
        return False

    allowed_sections = [
        "/newsfront/",
        "/politics/",
        "/world/",
        "/thewire/",
        "/us/",
        "/headline/",
    ]

    return any(section in low for section in allowed_sections)


def should_skip(title, url):
    title_l = title.lower()

    if len(title) < 20:
        return True, "too short"

    bad_title_bits = [
        "full story",
        "more ",
        "newsmax tv",
        "war against iran",
        "trump administration",
        "newsfront",
        "politics",
        "opinion",
        "podcast",
        "platinum",
        "subscribe",
        "advertisement",
        "watch ",
        "read more",
    ]

    if any(bit == title_l or title_l.startswith(bit) for bit in bad_title_bits):
        return True, "section/UI title"

    if not is_article_url(url):
        return True, "not article URL"

    return False, "candidate"


def score_candidate(item):
    title = item["title"].lower()
    url = item["url"].lower()
    top = float(item.get("top", 99999))
    index = item.get("index", 9999)

    score = 1000.0

    # Favor items visually near the top of the page, but below the navigation.
    if 100 <= top <= 1100:
        score += 800 - min(top, 800) * 0.55
    elif top < 100:
        score -= 400
    else:
        score -= min((top - 1100) * 0.20, 350)

    # Earlier article links generally correspond to top/lead story cards.
    score += max(0, 320 - index * 3)

    if "/newsfront/" in url:
        score += 120

    if any(word in title for word in [
        "trump",
        "iran",
        "israel",
        "white house",
        "supreme court",
        "pentagon",
        "war",
    ]):
        score += 50

    if len(title) > 145:
        score -= 80

    return score


def get_homepage_candidates(ws_url):
    js = r"""
(() => {
    return Array.from(document.querySelectorAll("a[href]")).map((a, index) => {
        const rect = a.getBoundingClientRect();

        return {
            index,
            href: a.href || "",
            text: (a.innerText || a.textContent || "").replace(/\s+/g, " ").trim(),
            aria: (a.getAttribute("aria-label") || "").replace(/\s+/g, " ").trim(),
            titleAttr: (a.getAttribute("title") || "").replace(/\s+/g, " ").trim(),
            className: String(a.className || ""),
            top: rect.top + window.scrollY,
            left: rect.left,
            width: rect.width,
            height: rect.height
        };
    });
})()
"""
    return cdp_eval(ws_url, js)


def get_article_text(ws_url):
    js = r"""
(() => {
    // Try to dismiss common consent dialogs first.
    const acceptButtons = Array.from(
        document.querySelectorAll("button, a, input[type='button'], input[type='submit']")
    );

    for (const button of acceptButtons) {
        const label = (
            button.innerText ||
            button.value ||
            button.getAttribute("aria-label") ||
            ""
        ).replace(/\s+/g, " ").trim().toLowerCase();

        if (
            label === "accept" ||
            label === "accept all" ||
            label === "allow all" ||
            label === "i accept" ||
            label === "agree"
        ) {
            try {
                button.click();
                break;
            } catch (error) {}
        }
    }

    const removeSelectors = [
        "script",
        "style",
        "noscript",
        "nav",
        "header",
        "footer",
        "aside",
        "form",
        "button",
        "iframe",
        "[id*='cookie']",
        "[class*='cookie']",
        "[id*='consent']",
        "[class*='consent']",
        "[id*='privacy']",
        "[class*='privacy']",
        "[id*='onetrust']",
        "[class*='onetrust']",
        "[id*='banner']",
        "[class*='banner']",
        "[id*='modal']",
        "[class*='modal']",
        "[role='dialog']",
        "[aria-modal='true']",
        ".advertisement",
        ".ad",
        "[class*='advert']",
        "[id*='advert']",
        ".social-share",
        ".share-tools",
        ".related",
        ".recommended",
        ".newsletter",
    ];

    for (const selector of removeSelectors) {
        document.querySelectorAll(selector).forEach(node => {
            try {
                node.remove();
            } catch (error) {}
        });
    }

    const headlineNode =
        document.querySelector("article h1") ||
        document.querySelector("main h1") ||
        document.querySelector("h1");

    const headline = headlineNode
        ? (headlineNode.innerText || headlineNode.textContent || "")
            .replace(/\s+/g, " ")
            .trim()
        : "";

    const articleRoot =
        document.querySelector("article") ||
        document.querySelector('[itemprop="articleBody"]') ||
        document.querySelector('[class*="article-body"]') ||
        document.querySelector('[class*="ArticleBody"]') ||
        document.querySelector("main") ||
        document.body;

    const paragraphs = Array.from(
        articleRoot.querySelectorAll("p")
    )
        .map(node => (node.innerText || node.textContent || "").replace(/\s+/g, " ").trim())
        .filter(text => {
            if (text.length < 45) return false;

            const low = text.toLowerCase();

            const blocked = [
                "privacy preference center",
                "strictly necessary cookies",
                "functional cookies",
                "analytics cookies",
                "marketing cookies",
                "manage consent preferences",
                "we and our partners",
                "advertisement",
                "sign up for",
                "follow us",
                "copyright",
            ];

            return !blocked.some(bit => low.includes(bit));
        });

    let text = paragraphs.join("\n\n").trim();

    // Fallback if paragraphs were not found.
    if (text.length < 200) {
        const clone = articleRoot.cloneNode(true);

        clone.querySelectorAll(
            "script, style, noscript, nav, header, footer, aside, form, button, iframe," +
            "[id*='cookie'], [class*='cookie'], [id*='consent'], [class*='consent']," +
            "[id*='privacy'], [class*='privacy'], [id*='onetrust'], [class*='onetrust']," +
            "[role='dialog'], [aria-modal='true']"
        ).forEach(node => node.remove());

        text = (clone.innerText || clone.textContent || "")
            .replace(/\n{3,}/g, "\n\n")
            .replace(/[ \t]+\n/g, "\n")
            .replace(/\s+/g, " ")
            .trim();
    }

    return {
        pageTitle: document.title || "",
        headline,
        html: document.documentElement.outerHTML || "",
        text
    };
})()
"""
    return cdp_eval(ws_url, js)


def main():
    print("Looking for Chrome remote-debugging tabs...")

    try:
        tabs = get_tabs()
    except Exception as error:
        print("Could not connect to Chrome remote debugging.")
        print(error)
        sys.exit(1)

    print(f"Chrome tabs found: {len(tabs)}")

    tab = choose_newsmax_tab(tabs)

    if not tab:
        print("No Newsmax tab found.")
        print("Open https://www.newsmax.com/ in the separate debug Chrome window.")
        sys.exit(1)

    ws_url = tab["webSocketDebuggerUrl"]

    print("Using homepage tab:")
    print("Title:", tab.get("title", ""))
    print("URL:", tab.get("url", ""))

    time.sleep(1)

    home_html = cdp_eval(ws_url, "document.documentElement.outerHTML")
    HOME_HTML_OUT.write_text(home_html, encoding="utf-8", errors="replace")

    print("")
    print("Saved homepage HTML:", HOME_HTML_OUT)
    print("Homepage HTML bytes:", len(home_html.encode("utf-8")))

    raw_candidates = get_homepage_candidates(ws_url)

    candidates = []
    seen = set()

    for item in raw_candidates:
        url = urljoin(HOME_URL, item.get("href", ""))
        title = clean(item.get("text") or item.get("aria") or item.get("titleAttr"))

        skip, reason = should_skip(title, url)

        if skip:
            continue

        key = (title.lower(), url.lower())

        if key in seen:
            continue

        seen.add(key)

        candidate = {
            "index": item.get("index", 9999),
            "title": title,
            "url": url,
            "top": item.get("top", 99999),
            "left": item.get("left", 0),
            "width": item.get("width", 0),
            "height": item.get("height", 0),
            "reason": reason,
        }

        candidate["score"] = score_candidate(candidate)
        candidates.append(candidate)

    candidates.sort(key=lambda item: item["score"], reverse=True)

    print("")
    print("================ NEWSMAX HOMEPAGE CANDIDATES ================")

    for i, item in enumerate(candidates[:30], 1):
        status = "SELECT" if i == 1 else "KEEP"

        print(
            f'{i:02d}. {status} score={item["score"]:.1f} '
            f'top={item["top"]:.0f} index={item["index"]}'
        )
        print(f'    title={item["title"]}')
        print(f'    url={item["url"]}')

    if not candidates:
        raise RuntimeError("No usable Newsmax homepage article candidates found")

    selected = candidates[0]

    print("")
    print("================ SELECTED NEWSMAX STORY ================")
    print(f'Title: "{selected["title"]}"')
    print(f'URL: {selected["url"]}')

    print("")
    print("Navigating the Chrome tab to the selected article...")

    cdp_navigate(ws_url, selected["url"])
    time.sleep(3)

    article = get_article_text(ws_url)

    ARTICLE_HTML_OUT.write_text(
        article.get("html", ""),
        encoding="utf-8",
        errors="replace",
    )

    ARTICLE_TEXT_OUT.write_text(
        article.get("text", ""),
        encoding="utf-8",
        errors="replace",
    )

    print("")
    print("================ ARTICLE EXTRACTION ================")
    print("Article page title:", article.get("title", ""))
    print("Saved article HTML:", ARTICLE_HTML_OUT)
    print("Saved article text:", ARTICLE_TEXT_OUT)
    print("Article text characters:", len(article.get("text", "")))

    print("")
    print("FIRST 3000 ARTICLE TEXT CHARACTERS:")
    print(article.get("text", "")[:3000])


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print("")
        print("================ FINAL OUTPUT ================")
        print(f"ERROR: {error}")
        print("================================================")
        sys.exit(1)
