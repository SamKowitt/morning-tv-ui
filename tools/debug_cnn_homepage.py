import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from services.newsmax_chrome import (
    _close_page,
    _create_page,
    _eval,
    _navigate,
)


def main():
    target_id = ""
    ws_url = ""

    try:
        target_id, ws_url = _create_page()
        _navigate(ws_url, "https://www.cnn.com/")

        candidates = _eval(
            ws_url,
            r"""
(() => {
    const clean = value => String(value || "")
        .replace(/\s+/g, " ")
        .trim();

    const visible = element => {
        if (!element) return false;

        const style = getComputedStyle(element);
        const rect = element.getBoundingClientRect();

        return (
            style.display !== "none" &&
            style.visibility !== "hidden" &&
            Number(style.opacity || 1) > 0 &&
            rect.width > 40 &&
            rect.height > 12 &&
            rect.bottom > 0
        );
    };

    const articleUrl = href => {
        try {
            const url = new URL(href);
            const host = url.hostname.toLowerCase();
            const path = url.pathname.toLowerCase();

            if (!(host === "cnn.com" || host.endsWith(".cnn.com"))) {
                return false;
            }

            if (!/^\/202\d\//.test(path)) {
                return false;
            }

            const blocked = [
                "/audio/",
                "/podcasts/",
                "/videos/",
                "/video/",
                "/espanol/",
                "/listen/",
                "/cnn-underscored/"
            ];

            return !blocked.some(bit => path.includes(bit));
        } catch {
            return false;
        }
    };

    const blockedText = [
        "chasing life with dr. sanjay gupta",
        "all there is with anderson cooper",
        "the assignment with audie cornish",
        "podcast",
        "audio",
        "newsletter",
        "subscribe",
        "watch live",
        "listen to"
    ];

    const found = [];
    const seen = new Set();

    for (const link of document.querySelectorAll("a[href]")) {
        if (!visible(link) || !articleUrl(link.href)) {
            continue;
        }

        if (
            link.closest("footer") ||
            link.closest("nav") ||
            link.closest("[role='navigation']")
        ) {
            continue;
        }

        const nodes = [
            ...link.querySelectorAll(
                "h1, h2, h3, h4, h5, h6, " +
                "[class*='headline'], [class*='Headline'], " +
                "[class*='title'], [class*='Title']"
            ),
            link
        ].filter(visible);

        let best = null;

        for (const node of nodes) {
            const title = clean(node.innerText || node.textContent);
            const lower = title.toLowerCase();

            if (
                title.length < 20 ||
                blockedText.some(bit => lower.includes(bit))
            ) {
                continue;
            }

            const style = getComputedStyle(node);
            const rect = node.getBoundingClientRect();
            const fontSize = Number.parseFloat(style.fontSize || "0") || 0;

            if (!best || fontSize > best.font_size) {
                best = {
                    title,
                    font_size: fontSize,
                    top: Math.round(rect.top),
                    left: Math.round(rect.left),
                    width: Math.round(rect.width),
                    height: Math.round(rect.height),
                    tag: node.tagName,
                    class_name: String(node.className || ""),
                };
            }
        }

        if (!best) {
            continue;
        }

        const card =
            link.closest("article") ||
            link.closest("section") ||
            link.closest("li") ||
            link.parentElement ||
            link;

        const cardRect = card.getBoundingClientRect();
        const key = `${link.href}|${best.title.toLowerCase()}`;

        if (seen.has(key)) {
            continue;
        }

        seen.add(key);

        found.push({
            ...best,
            link: link.href,
            card_area: Math.round(cardRect.width * cardRect.height),
            card_tag: card.tagName,
            card_class: String(card.className || ""),
        });
    }

    return found;
})()
""",
            timeout=25,
        )

        candidates = list(candidates or [])

        candidates.sort(
            key=lambda item: (
                -float(item.get("font_size", 0) or 0),
                float(item.get("top", 999999) or 999999),
                -float(item.get("card_area", 0) or 0),
            )
        )

        print("\n================ CNN RENDERED HEADLINE DEBUG ================")
        print(f"Visible editorial candidates found: {len(candidates)}")

        print("\n--- Largest rendered headlines first ---")
        for index, item in enumerate(candidates[:20], start=1):
            print(
                f"\n{index}. font={item['font_size']:.1f}px "
                f"top={item['top']} left={item['left']} "
                f"card_area={item['card_area']}"
            )
            print(f"   title: {item['title']}")
            print(f"   url:   {item['link']}")
            print(f"   node:  {item['tag']} | {item['class_name'][:180]}")
            print(f"   card:  {item['card_tag']} | {item['card_class'][:180]}")

        print("\n--- Current text-size-first proposed selection ---")
        for index, item in enumerate(candidates[:6], start=1):
            label = "LEAD" if index == 1 else f"TOP STORY {index - 1}"
            print(f"{label}: {item['title']}")
            print(f"  font={item['font_size']:.1f}px top={item['top']}")
            print(f"  {item['link']}")

    finally:
        if target_id:
            _close_page(target_id)


if __name__ == "__main__":
    main()
