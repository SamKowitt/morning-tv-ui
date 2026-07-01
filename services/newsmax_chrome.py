import json
import re
import time
import urllib.request
from urllib.parse import urljoin, urlparse

from websocket import create_connection


DEBUG_BASE = "http://127.0.0.1:9222"
DEBUG_ORIGIN = "http://127.0.0.1:9222"
CHROME_TIMEOUT = 8
PAGE_TIMEOUT = 14


def _clean(value):
    value = str(value or "")
    value = re.sub(r"\s+", " ", value).strip()
    value = re.sub(r"\s+\[?Full Story\]?\s*$", "", value, flags=re.I).strip()
    value = re.sub(r"\s+\|\s+Newsmax\.com\s*$", "", value, flags=re.I).strip()
    return value


def _json_url(path):
    with urllib.request.urlopen(
        f"{DEBUG_BASE}{path}",
        timeout=CHROME_TIMEOUT,
    ) as response:
        return json.loads(response.read().decode("utf-8"))


def _browser_ws_url():
    version = _json_url("/json/version")
    ws_url = version.get("webSocketDebuggerUrl", "")

    if not ws_url:
        raise RuntimeError(
            "Chrome debugging is not available on port 9222. "
            "Start the separate Chrome window with remote debugging first."
        )

    return ws_url


def _cdp_call(ws_url, method, params=None, timeout=CHROME_TIMEOUT):
    ws = create_connection(
        ws_url,
        timeout=timeout,
        origin=DEBUG_ORIGIN,
    )

    try:
        request_id = 1

        ws.send(json.dumps({
            "id": request_id,
            "method": method,
            "params": params or {},
        }))

        deadline = time.time() + timeout

        while time.time() < deadline:
            message = json.loads(ws.recv())

            if message.get("id") == request_id:
                if "error" in message:
                    raise RuntimeError(
                        f"Chrome DevTools error for {method}: "
                        f"{message['error']}"
                    )

                return message.get("result", {})

        raise TimeoutError(f"Chrome DevTools timed out during {method}")

    finally:
        ws.close()


def _create_page():
    result = _cdp_call(
        _browser_ws_url(),
        "Target.createTarget",
        {"url": "about:blank"},
    )

    target_id = result.get("targetId", "")

    if not target_id:
        raise RuntimeError("Chrome did not create a Newsmax page target")

    deadline = time.time() + CHROME_TIMEOUT

    while time.time() < deadline:
        tabs = _json_url("/json")

        for tab in tabs:
            if tab.get("id") == target_id and tab.get("webSocketDebuggerUrl"):
                return target_id, tab["webSocketDebuggerUrl"]

        time.sleep(0.15)

    raise RuntimeError("Chrome created a target but did not expose its debugger URL")


def _close_page(target_id):
    try:
        _cdp_call(
            _browser_ws_url(),
            "Target.closeTarget",
            {"targetId": target_id},
            timeout=4,
        )
    except Exception:
        pass


def _eval(ws_url, expression, timeout=CHROME_TIMEOUT):
    result = _cdp_call(
        ws_url,
        "Runtime.evaluate",
        {
            "expression": expression,
            "returnByValue": True,
            "awaitPromise": True,
        },
        timeout=timeout,
    )

    value = result.get("result", {}).get("value", "")

    if value is None:
        return ""

    return value


def _navigate(ws_url, url):
    _cdp_call(
        ws_url,
        "Page.enable",
        timeout=CHROME_TIMEOUT,
    )

    _cdp_call(
        ws_url,
        "Network.enable",
        timeout=CHROME_TIMEOUT,
    )

    _cdp_call(
        ws_url,
        "Emulation.setDeviceMetricsOverride",
        {
            "width": 1440,
            "height": 1200,
            "deviceScaleFactor": 1,
            "mobile": False,
        },
        timeout=CHROME_TIMEOUT,
    )

    _cdp_call(
        ws_url,
        "Network.setUserAgentOverride",
        {
            "userAgent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/149.0.0.0 Safari/537.36"
            ),
            "acceptLanguage": "en-US,en;q=0.9",
            "platform": "macOS",
        },
        timeout=CHROME_TIMEOUT,
    )

    _cdp_call(
        ws_url,
        "Page.navigate",
        {"url": url},
        timeout=CHROME_TIMEOUT,
    )

    deadline = time.time() + PAGE_TIMEOUT

    while time.time() < deadline:
        state = _eval(ws_url, "document.readyState", timeout=4)

        if state in {"interactive", "complete"}:
            time.sleep(3.5)
            return

        time.sleep(0.2)

    raise TimeoutError(f"Page did not finish loading within {PAGE_TIMEOUT} seconds")


def _is_newsmax_article_url(url):
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    path = parsed.path.lower()

    if not (host == "newsmax.com" or host.endswith(".newsmax.com")):
        return False

    blocked = [
        "/video/",
        "/videos/",
        "/tv/",
        "/health/",
        "/money/",
        "/books/",
        "/bestlists/",
        "/subscribe",
        "/login",
        "/privacy",
        "/terms",
        "/contact",
    ]

    return not any(bit in path for bit in blocked)


def _should_skip_title(title):
    lowered = title.lower()

    if len(title) < 20:
        return True

    blocked = [
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

    return any(
        lowered == item or lowered.startswith(item)
        for item in blocked
    )


def _score_candidate(item):
    top = float(item.get("top", 99999))
    index = int(item.get("index", 9999))
    title = item["title"].lower()
    url = item["url"].lower()

    score = 1000.0

    if 100 <= top <= 1000:
        score += 850 - min(top, 850) * 0.60
    elif top < 100:
        score -= 450
    else:
        score -= min((top - 1000) * 0.20, 420)

    score += max(0, 330 - index * 3)

    if "/newsfront/" in url:
        score += 80

    if any(word in title for word in [
        "trump",
        "iran",
        "israel",
        "white house",
        "supreme court",
        "pentagon",
        "war",
    ]):
        score += 45

    if len(title) > 150:
        score -= 90

    return score


def fetch_newsmax_homepage_article():
    """
    Newsmax homepage resolver.

    The breaking-news banner and the main homepage article are separate page
    regions. The banner is returned as supplemental breaking_headline text;
    the actual lead article always comes from the canvas-one lead module.
    """
    target_id = ""
    ws_url = ""

    try:
        target_id, ws_url = _create_page()
        _navigate(ws_url, "https://www.newsmax.com/")

        payload = _eval(
            ws_url,
            r"""
(() => {
    const clean = value => (value || "")
        .replace(/\s+/g, " ")
        .trim()
        .replace(/\s+\[?Full Story\]?\s*$/i, "")
        .replace(/\s+\|\s+Newsmax\.com\s*$/i, "");

    const breakingRoot = document.querySelector("#nmBreakingNewsCont");

    const breakingLink =
        breakingRoot?.querySelector("#nmBreakingText h2 a") ||
        breakingRoot?.querySelector("#nmBreakingText a") ||
        breakingRoot?.querySelector("h2 a") ||
        breakingRoot?.querySelector("a[href]");

    const leadLink =
        document.querySelector("#nmCanvas1Headline h1 a") ||
        document.querySelector("#nmCanvas1Headline a[href]") ||
        document.querySelector("#nmCanvas1 h1 a");

    const leadHeading =
        document.querySelector("#nmCanvas1Headline h1") ||
        document.querySelector("#nmCanvas1 h1");

    const normalize = value => clean(value).toLowerCase();

    const leadTitleKey = normalize(
        leadLink
            ? (leadLink.innerText || leadLink.textContent || "")
            : (
                leadHeading
                    ? (leadHeading.innerText || leadHeading.textContent || "")
                    : ""
            )
    );

    const isVisibleImage = image => {
        const style = window.getComputedStyle(image);
        const rect = image.getBoundingClientRect();

        return (
            style.display !== "none" &&
            style.visibility !== "hidden" &&
            Number(style.opacity || 1) > 0 &&
            rect.width >= 120 &&
            rect.height >= 90
        );
    };

    const homepageLeadImages = Array.from(document.querySelectorAll("img"))
        .map(image => {
            const rect = image.getBoundingClientRect();

            return {
                alt: clean(image.alt || ""),
                src: String(
                    image.currentSrc ||
                    image.src ||
                    image.getAttribute("data-src") ||
                    image.getAttribute("data-lazy-src") ||
                    ""
                ).trim(),
                visible: isVisibleImage(image),
                width: Math.round(rect.width),
                height: Math.round(rect.height)
            };
        })
        .filter(item =>
            item.visible &&
            item.src &&
            !item.src.startsWith("data:") &&
            item.width >= 120 &&
            item.height >= 90
        );

    const exactLeadImage = homepageLeadImages.find(
        item => normalize(item.alt) === leadTitleKey
    );

    const leadImageUrl = exactLeadImage
        ? exactLeadImage.src
        : "";

    return {
        breakingHeadline: clean(
            breakingLink
                ? (breakingLink.innerText || breakingLink.textContent || "")
                : ""
        ),
        breakingUrl: breakingLink ? (breakingLink.href || "") : "",
        leadHeadline: clean(
            leadLink
                ? (leadLink.innerText || leadLink.textContent || "")
                : (leadHeading ? (leadHeading.innerText || leadHeading.textContent || "") : "")
        ),
        leadUrl: leadLink ? (leadLink.href || "") : "",
        leadImageUrl,
        pageTitle: document.title || ""
    };
})()
""",
            timeout=PAGE_TIMEOUT,
        )

        if not isinstance(payload, dict):
            raise RuntimeError("Chrome did not return Newsmax homepage payload")

        breaking_headline = _clean(payload.get("breakingHeadline", ""))
        lead_title = _clean(payload.get("leadHeadline", ""))
        lead_url = urljoin(
            "https://www.newsmax.com/",
            str(payload.get("leadUrl", "") or ""),
        )
        lead_image_url = urljoin(
            "https://www.newsmax.com/",
            str(payload.get("leadImageUrl", "") or ""),
        )

        if not lead_title or not lead_url:
            raise RuntimeError(
                "Newsmax homepage lead was not found in #nmCanvas1Headline. "
                f"Page title: {payload.get('pageTitle', '')!r}"
            )

        if not _is_newsmax_article_url(lead_url):
            raise RuntimeError(
                f"Newsmax canvas-one lead URL was not a valid article URL: {lead_url}"
            )

        if _should_skip_title(lead_title):
            raise RuntimeError(
                f"Newsmax canvas-one lead title was not usable: {lead_title!r}"
            )

        print(f'NEWSMAX BREAKING HEADLINE: "{breaking_headline}"')
        print(f'NEWSMAX ACTUAL LEAD: "{lead_title}"')
        print(f'NEWSMAX ACTUAL LEAD LINK: "{lead_url}"')
        print(f'NEWSMAX CANVAS-ONE LEAD IMAGE: "{lead_image_url}"')

        return {
            "title": lead_title,
            "link": lead_url,
            "image_url": lead_image_url,
            "image_bytes": b"",
            "breaking_headline": breaking_headline,
            "breaking_url": str(payload.get("breakingUrl", "") or ""),
        }

    finally:
        if target_id:
            _close_page(target_id)

def fetch_newsmax_article_payload(url):
    if not _is_newsmax_article_url(url):
        raise RuntimeError("This is not a valid Newsmax article URL")

    target_id = ""
    ws_url = ""

    try:
        target_id, ws_url = _create_page()
        _navigate(ws_url, url)

        payload = _eval(
            ws_url,
            r"""
(() => {
    const buttonCandidates = Array.from(
        document.querySelectorAll("button, input[type='button'], input[type='submit'], a")
    );

    for (const button of buttonCandidates) {
        const label = (
            button.innerText ||
            button.value ||
            button.getAttribute("aria-label") ||
            ""
        ).replace(/\s+/g, " ").trim().toLowerCase();

        if ([
            "accept",
            "accept all",
            "allow all",
            "i accept",
            "agree"
        ].includes(label)) {
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
        "[role='dialog']",
        "[aria-modal='true']",
        "[class*='advert']",
        "[id*='advert']",
        "[class*='related']",
        "[class*='recommended']",
        "[class*='newsletter']"
    ];

    for (const selector of removeSelectors) {
        document.querySelectorAll(selector).forEach(node => {
            try { node.remove(); } catch (error) {}
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

    const blockedText = [
        "privacy preference center",
        "strictly necessary cookies",
        "functional cookies",
        "analytics cookies",
        "marketing cookies",
        "manage consent preferences",
        "advertisement",
        "sign up for",
        "follow us",
        "copyright"
    ];

    const paragraphs = Array.from(articleRoot.querySelectorAll("p"))
        .map(node => (node.innerText || node.textContent || "")
            .replace(/\s+/g, " ")
            .trim()
        )
        .filter(text => {
            if (text.length < 45) return false;
            const low = text.toLowerCase();
            return !blockedText.some(bit => low.includes(bit));
        });

    let text = paragraphs.join("\n\n").trim();

    if (text.length < 180) {
        const fallback = (articleRoot.innerText || articleRoot.textContent || "")
            .replace(/\n{3,}/g, "\n\n")
            .replace(/[ \t]+\n/g, "\n")
            .trim();

        const lines = fallback
            .split(/\n+/)
            .map(line => line.replace(/\s+/g, " ").trim())
            .filter(line => {
                if (line.length < 45) return false;
                const low = line.toLowerCase();
                return !blockedText.some(bit => low.includes(bit));
            });

        text = lines.join("\n\n").trim();
    }

    return {
        title: headline,
        text
    };
})()
""",
            timeout=PAGE_TIMEOUT,
        )

        if not isinstance(payload, dict):
            raise RuntimeError("Chrome returned an invalid Newsmax article payload")

        title = _clean(payload.get("title", ""))
        text = str(payload.get("text", "") or "").strip()

        if len(text) < 120:
            raise RuntimeError("Newsmax page loaded, but no readable article text was found")

        return {
            "is_live": False,
            "method": "newsmax_chrome",
            "text": text,
            "updates": [],
            "headline": title,
        }

    finally:
        if target_id:
            _close_page(target_id)


# --- Newsmax article-body override: broader Chrome DOM extraction ---
def fetch_newsmax_article_payload(url):
    if not _is_newsmax_article_url(url):
        raise RuntimeError("This is not a valid Newsmax article URL")

    target_id = ""
    ws_url = ""

    try:
        target_id, ws_url = _create_page()
        _navigate(ws_url, url)

        # Newsmax can populate the story body a little after the initial page load.
        deadline = time.time() + 12
        last_payload = {}

        while time.time() < deadline:
            payload = _eval(
                ws_url,
                r"""
(() => {
    const buttonCandidates = Array.from(
        document.querySelectorAll("button, input[type='button'], input[type='submit'], a")
    );

    for (const button of buttonCandidates) {
        const label = (
            button.innerText ||
            button.value ||
            button.getAttribute("aria-label") ||
            ""
        ).replace(/\s+/g, " ").trim().toLowerCase();

        if ([
            "accept",
            "accept all",
            "allow all",
            "i accept",
            "agree"
        ].includes(label)) {
            try {
                button.click();
                break;
            } catch (error) {}
        }
    }

    const removeSelectors = [
        "script", "style", "noscript", "nav", "header", "footer",
        "aside", "form", "button", "iframe",
        "[id*='cookie']", "[class*='cookie']",
        "[id*='consent']", "[class*='consent']",
        "[id*='privacy']", "[class*='privacy']",
        "[id*='onetrust']", "[class*='onetrust']",
        "[role='dialog']", "[aria-modal='true']",
        "[class*='advert']", "[id*='advert']",
        "[class*='related']", "[class*='recommended']",
        "[class*='newsletter']", "[class*='share']"
    ];

    for (const selector of removeSelectors) {
        document.querySelectorAll(selector).forEach(node => {
            try { node.remove(); } catch (error) {}
        });
    }

    const normalize = value => (value || "")
        .replace(/\s+/g, " ")
        .trim();

    const blocked = [
        "privacy preference center",
        "strictly necessary cookies",
        "functional cookies",
        "analytics cookies",
        "marketing cookies",
        "manage consent preferences",
        "cookie list",
        "advertisement",
        "sign up for",
        "follow us",
        "all rights reserved",
        "search by queryly",
        "advanced search"
    ];

    const keep = value => {
        const text = normalize(value);

        if (text.length < 45) return false;

        const low = text.toLowerCase();

        return !blocked.some(bit => low.includes(bit));
    };

    const headlineNode =
        document.querySelector("article h1") ||
        document.querySelector("main h1") ||
        document.querySelector("h1");

    const headline = normalize(
        headlineNode ? (headlineNode.innerText || headlineNode.textContent) : ""
    );

    const roots = [
        document.querySelector('[itemprop="articleBody"]'),
        document.querySelector('[class*="article-body"]'),
        document.querySelector('[class*="ArticleBody"]'),
        document.querySelector('[class*="articleBody"]'),
        document.querySelector("article"),
        document.querySelector("main"),
        document.body
    ].filter(Boolean);

    const seen = new Set();
    const paragraphs = [];

    for (const root of roots) {
        for (const node of root.querySelectorAll("p, blockquote")) {
            const text = normalize(node.innerText || node.textContent);

            if (!keep(text)) continue;

            const key = text.toLowerCase();

            if (seen.has(key)) continue;

            seen.add(key);
            paragraphs.push(text);
        }

        if (paragraphs.length >= 3) break;
    }

    let text = paragraphs.join("\n\n").trim();

    // Last-resort fallback: use visible body lines while excluding site furniture.
    if (text.length < 180) {
        const lines = (document.body.innerText || "")
            .split(/\n+/)
            .map(normalize)
            .filter(keep);

        const unique = [];
        const fallbackSeen = new Set();

        for (const line of lines) {
            const key = line.toLowerCase();

            if (fallbackSeen.has(key)) continue;

            fallbackSeen.add(key);
            unique.push(line);
        }

        text = unique.join("\n\n").trim();
    }

    return {
        title: headline,
        text,
        pageTitle: document.title || "",
        bodyPreview: normalize(document.body ? document.body.innerText.slice(0, 1200) : "")
    };
})()
""",
                timeout=PAGE_TIMEOUT,
            )

            if isinstance(payload, dict):
                last_payload = payload
                text = str(payload.get("text", "") or "").strip()

                if len(text) >= 180:
                    return {
                        "is_live": False,
                        "method": "newsmax_chrome",
                        "text": text,
                        "updates": [],
                        "headline": _clean(payload.get("title", "")),
                    }

            time.sleep(1)

        page_title = _clean(last_payload.get("pageTitle", ""))
        preview = _clean(last_payload.get("bodyPreview", ""))

        raise RuntimeError(
            "Newsmax article loaded but readable story paragraphs were not found. "
            f"Page title: {page_title!r}. "
            f"Visible-text preview: {preview[:500]!r}"
        )

    finally:
        if target_id:
            _close_page(target_id)


# --- Final Newsmax article extractor: read articleBody directly, do not mutate DOM ---
def fetch_newsmax_article_payload(url):
    if not _is_newsmax_article_url(url):
        raise RuntimeError("This is not a valid Newsmax article URL")

    target_id = ""
    ws_url = ""

    try:
        target_id, ws_url = _create_page()
        _navigate(ws_url, url)

        payload = _eval(
            ws_url,
            r"""
(() => {
    const clean = value => (value || "")
        .replace(/\s+/g, " ")
        .trim();

    const blocked = [
        "privacy preference center",
        "strictly necessary cookies",
        "functional cookies",
        "analytics cookies",
        "marketing cookies",
        "manage consent preferences",
        "cookie list",
        "advertisement",
        "receive breaking news",
        "all rights reserved",
        "sign up for",
        "follow us",
        "search by queryly",
        "advanced search"
    ];

    const allowed = value => {
        const text = clean(value);

        if (text.length < 45) return false;

        const low = text.toLowerCase();

        return !blocked.some(bit => low.includes(bit));
    };

    const headlineNode =
        document.querySelector("h1");

    const headline = clean(
        headlineNode ? (headlineNode.innerText || headlineNode.textContent) : ""
    );

    const root =
        document.querySelector("[itemprop='articleBody']") ||
        document.querySelector("[itemprop='articlebody']") ||
        document.querySelector("article") ||
        document.body;

    const paragraphs = Array.from(root.querySelectorAll("p"))
        .map(node => clean(node.innerText || node.textContent))
        .filter(allowed);

    const seen = new Set();
    const uniqueParagraphs = [];

    for (const paragraph of paragraphs) {
        const key = paragraph.toLowerCase();

        if (seen.has(key)) continue;

        seen.add(key);
        uniqueParagraphs.push(paragraph);
    }

    const text = uniqueParagraphs.join("\n\n").trim();

    return {
        title: headline,
        text,
        paragraphCount: uniqueParagraphs.length,
        rootName: root ? root.tagName : "",
        rootItemprop: root ? (root.getAttribute("itemprop") || "") : ""
    };
})()
""",
            timeout=15,
        )

        if not isinstance(payload, dict):
            raise RuntimeError("Chrome returned an invalid Newsmax article payload")

        text = str(payload.get("text", "") or "").strip()

        if len(text) < 160:
            raise RuntimeError(
                "Newsmax article body was found but did not contain enough readable text. "
                f"root={payload.get('rootName')!r}, "
                f"itemprop={payload.get('rootItemprop')!r}, "
                f"paragraphs={payload.get('paragraphCount')!r}"
            )

        return {
            "is_live": False,
            "method": "newsmax_chrome_articleBody",
            "text": text,
            "updates": [],
            "headline": _clean(payload.get("title", "")),
        }

    finally:
        if target_id:
            _close_page(target_id)


# --- Newsmax card image lookup through headless Chrome ---
def fetch_newsmax_article_image_url(url):
    if not _is_newsmax_article_url(url):
        return ""

    target_id = ""
    ws_url = ""

    try:
        target_id, ws_url = _create_page()
        _navigate(ws_url, url)

        image_url = _eval(
            ws_url,
            r"""
(() => {
    const cleanUrl = value => {
        const url = String(value || "").trim();

        if (!url) return "";
        if (url.startsWith("data:")) return "";
        if (url.includes("logo")) return "";
        if (url.includes("icon")) return "";
        if (url.includes("avatar")) return "";
        if (url.includes("placeholder")) return "";

        return url;
    };

    const metaSelectors = [
        'meta[property="og:image"]',
        'meta[name="og:image"]',
        'meta[name="twitter:image"]',
        'meta[name="twitter:image:src"]'
    ];

    for (const selector of metaSelectors) {
        const node = document.querySelector(selector);
        const value = cleanUrl(node?.content);

        if (value) return value;
    }

    const articleRoot =
        document.querySelector("[itemprop='articleBody']") ||
        document.querySelector("[class*='article']") ||
        document.body;

    const images = Array.from(document.images)
        .map(img => ({
            src: cleanUrl(img.currentSrc || img.src),
            width: img.naturalWidth || img.width || 0,
            height: img.naturalHeight || img.height || 0,
            distance: articleRoot.contains(img) ? 0 : 1
        }))
        .filter(item =>
            item.src &&
            item.width >= 280 &&
            item.height >= 150
        )
        .sort((a, b) => {
            if (a.distance !== b.distance) return a.distance - b.distance;
            return (b.width * b.height) - (a.width * a.height);
        });

    return images.length ? images[0].src : "";
})()
""",
            timeout=15,
        )

        image_url = str(image_url or "").strip()

        if image_url:
            print(f"NEWSMAX CHROME IMAGE: {image_url}")
        else:
            print("NEWSMAX CHROME IMAGE: none found")

        return image_url

    finally:
        if target_id:
            _close_page(target_id)


# --- Newsmax image download through headless Chrome ---
def fetch_newsmax_image_bytes(image_url):
    import base64

    image_url = str(image_url or "").strip()

    if not image_url:
        return b""

    target_id = ""
    ws_url = ""

    try:
        target_id, ws_url = _create_page()

        # Load a Newsmax page first so the fetch runs with Newsmax cookies/session.
        _navigate(ws_url, "https://www.newsmax.com/")

        encoded = _eval(
            ws_url,
            f"""
(async () => {{
    const imageUrl = {image_url!r};

    const response = await fetch(imageUrl, {{
        credentials: "include",
        cache: "force-cache"
    }});

    if (!response.ok) {{
        throw new Error(`Image fetch failed: ${{response.status}} ${{response.statusText}}`);
    }}

    const blob = await response.blob();

    if (!blob.type.startsWith("image/")) {{
        throw new Error(`Unexpected image content type: ${{blob.type}}`);
    }}

    return await new Promise((resolve, reject) => {{
        const reader = new FileReader();

        reader.onloadend = () => {{
            const value = String(reader.result || "");
            const comma = value.indexOf(",");
            resolve(comma >= 0 ? value.slice(comma + 1) : "");
        }};

        reader.onerror = () => reject(new Error("FileReader could not read image blob"));
        reader.readAsDataURL(blob);
    }});
}})()
""",
            timeout=20,
        )

        if not encoded:
            return b""

        image_bytes = base64.b64decode(encoded)

        print(f"NEWSMAX CHROME IMAGE DOWNLOAD OK: {len(image_bytes)} bytes")
        return image_bytes

    except Exception as error:
        print(f"NEWSMAX Chrome image download failed: {error}")
        return b""

    finally:
        if target_id:
            _close_page(target_id)


# --- Convert Newsmax image to JPEG through Chrome so Qt can display it ---
def fetch_newsmax_image_jpeg_bytes(image_url):
    import base64

    image_url = str(image_url or "").strip()

    if not image_url:
        return b""

    target_id = ""
    ws_url = ""

    try:
        target_id, ws_url = _create_page()
        _navigate(ws_url, "https://www.newsmax.com/")

        encoded = _eval(
            ws_url,
            f"""
(async () => {{
    const imageUrl = {image_url!r};

    const response = await fetch(imageUrl, {{
        credentials: "include",
        cache: "force-cache"
    }});

    if (!response.ok) {{
        throw new Error(`Image fetch failed: ${{response.status}}`);
    }}

    const blob = await response.blob();
    const bitmap = await createImageBitmap(blob);

    const canvas = document.createElement("canvas");
    canvas.width = bitmap.width;
    canvas.height = bitmap.height;

    const context = canvas.getContext("2d");
    context.drawImage(bitmap, 0, 0);

    return canvas.toDataURL("image/jpeg", 0.88).split(",", 2)[1];
}})()
""",
            timeout=20,
        )

        if not encoded:
            return b""

        data = base64.b64decode(encoded)

        print(f"NEWSMAX CHROME JPEG OK: {len(data)} bytes")
        return data

    except Exception as error:
        print(f"NEWSMAX Chrome JPEG conversion failed: {error}")
        return b""

    finally:
        if target_id:
            _close_page(target_id)


# ============================================================
# Automatic hidden Chrome lifecycle manager for Newsmax.
# Starts a separate headless Chrome only when needed, then closes
# it after all Newsmax work has finished and the app is idle.
# ============================================================

import atexit
import os
import signal
import subprocess
import threading


_NEWSMAX_CHROME_LOCK = threading.RLock()
_NEWSMAX_CHROME_PROCESS = None
_NEWSMAX_IDLE_TIMER = None
_NEWSMAX_ACTIVE_TARGETS = 0

_NEWSMAX_CHROME_PROFILE = os.path.expanduser("~/.newsmax-chrome-debug")
_NEWSMAX_CHROME_BINARY = (
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
)
_NEWSMAX_IDLE_SECONDS = 8


_ORIGINAL_BROWSER_WS_URL = _browser_ws_url
_ORIGINAL_CREATE_PAGE = _create_page
_ORIGINAL_CLOSE_PAGE = _close_page


def _newsmax_debug_server_ready():
    try:
        with urllib.request.urlopen(
            f"{DEBUG_BASE}/json/version",
            timeout=1.5,
        ) as response:
            payload = json.loads(response.read().decode("utf-8"))

        return bool(payload.get("webSocketDebuggerUrl"))

    except Exception:
        return False


def _cancel_newsmax_idle_shutdown_locked():
    global _NEWSMAX_IDLE_TIMER

    if _NEWSMAX_IDLE_TIMER is not None:
        _NEWSMAX_IDLE_TIMER.cancel()
        _NEWSMAX_IDLE_TIMER = None


def _start_newsmax_background_chrome_locked():
    global _NEWSMAX_CHROME_PROCESS

    if _newsmax_debug_server_ready():
        return

    if not os.path.exists(_NEWSMAX_CHROME_BINARY):
        raise RuntimeError(
            "Google Chrome was not found at "
            f"{_NEWSMAX_CHROME_BINARY}"
        )

    os.makedirs(_NEWSMAX_CHROME_PROFILE, exist_ok=True)

    command = [
        _NEWSMAX_CHROME_BINARY,
        "--headless=new",
        "--remote-debugging-port=9222",
        "--remote-allow-origins=*",
        f"--user-data-dir={_NEWSMAX_CHROME_PROFILE}",
        "--disable-gpu",
        "--no-first-run",
        "--no-default-browser-check",
    ]

    print("NEWSMAX: starting temporary hidden Chrome...")

    _NEWSMAX_CHROME_PROCESS = subprocess.Popen(
        command,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )

    deadline = time.time() + 12

    while time.time() < deadline:
        if _newsmax_debug_server_ready():
            print("NEWSMAX: hidden Chrome ready.")
            return

        if _NEWSMAX_CHROME_PROCESS.poll() is not None:
            raise RuntimeError(
                "Temporary Newsmax Chrome exited before opening "
                "its debugging connection."
            )

        time.sleep(0.2)

    raise TimeoutError(
        "Temporary Newsmax Chrome did not become ready on port 9222."
    )


def _ensure_newsmax_background_chrome():
    with _NEWSMAX_CHROME_LOCK:
        _cancel_newsmax_idle_shutdown_locked()
        _start_newsmax_background_chrome_locked()


def _shutdown_newsmax_background_chrome():
    global _NEWSMAX_CHROME_PROCESS
    global _NEWSMAX_IDLE_TIMER

    with _NEWSMAX_CHROME_LOCK:
        _NEWSMAX_IDLE_TIMER = None

        if _NEWSMAX_ACTIVE_TARGETS > 0:
            return

        process = _NEWSMAX_CHROME_PROCESS
        _NEWSMAX_CHROME_PROCESS = None

        if process is None:
            return

        if process.poll() is not None:
            return

        print("NEWSMAX: closing temporary hidden Chrome...")

        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        except Exception as error:
            print(f"NEWSMAX: hidden Chrome shutdown warning: {error}")


def _schedule_newsmax_idle_shutdown():
    global _NEWSMAX_IDLE_TIMER

    with _NEWSMAX_CHROME_LOCK:
        _cancel_newsmax_idle_shutdown_locked()

        if _NEWSMAX_ACTIVE_TARGETS > 0:
            return

        timer = threading.Timer(
            _NEWSMAX_IDLE_SECONDS,
            _shutdown_newsmax_background_chrome,
        )
        timer.daemon = True
        _NEWSMAX_IDLE_TIMER = timer
        timer.start()


def close_newsmax_background_chrome_now():
    """
    Optional immediate cleanup function.
    Safe to call during app shutdown.
    """
    global _NEWSMAX_ACTIVE_TARGETS

    with _NEWSMAX_CHROME_LOCK:
        _NEWSMAX_ACTIVE_TARGETS = 0
        _cancel_newsmax_idle_shutdown_locked()

    _shutdown_newsmax_background_chrome()


def _browser_ws_url():
    _ensure_newsmax_background_chrome()
    return _ORIGINAL_BROWSER_WS_URL()


def _create_page():
    global _NEWSMAX_ACTIVE_TARGETS

    _ensure_newsmax_background_chrome()

    target_id, ws_url = _ORIGINAL_CREATE_PAGE()

    with _NEWSMAX_CHROME_LOCK:
        _NEWSMAX_ACTIVE_TARGETS += 1
        _cancel_newsmax_idle_shutdown_locked()

    return target_id, ws_url


def _close_page(target_id):
    global _NEWSMAX_ACTIVE_TARGETS

    try:
        _ORIGINAL_CLOSE_PAGE(target_id)

    finally:
        with _NEWSMAX_CHROME_LOCK:
            if _NEWSMAX_ACTIVE_TARGETS > 0:
                _NEWSMAX_ACTIVE_TARGETS -= 1

        _schedule_newsmax_idle_shutdown()


atexit.register(close_newsmax_background_chrome_now)
