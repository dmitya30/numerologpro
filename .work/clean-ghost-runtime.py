from pathlib import Path
from urllib.parse import urlsplit
import html
import json
import re

FILES = [
    Path("index.html"),
    Path("elyor/index.html"),
    Path("quantocode/index.html"),
    Path("oracle/index.html"),
]
AGENTS = Path("AGENTS.md")

SCRIPT_RE = re.compile(r"<script\b[^>]*>.*?</script\s*>", re.I | re.S)
STYLE_RE = re.compile(r"<style\b[^>]*>.*?</style\s*>", re.I | re.S)
LINK_RE = re.compile(r"<link\b[^>]*>", re.I | re.S)
META_RE = re.compile(r"<meta\b[^>]*>", re.I | re.S)
TITLE_RE = re.compile(r"<title\b[^>]*>.*?</title\s*>", re.I | re.S)
TAG_RE = re.compile(r"<[^>]+>", re.S)
A_OPEN_RE = re.compile(r"<a\b[^>]*>", re.I | re.S)
HREF_RE = re.compile(r"(\bhref\s*=\s*)([\"\x27])(.*?)\2", re.I | re.S)

GHOST_SCRIPT_SIGNALS = (
    "cdn.jsdelivr.net/ghost/",
    "portal.min.js",
    "sodo-search",
    "comments-ui",
    "comment-counts",
    "ghost/api/",
    "members/api/",
)

GHOST_LINK_SIGNALS = (
    "ghost/api/",
    "members/api/",
    "webmention",
    "comment-counts",
)

ANALYTICS_SIGNALS = (
    "googletagmanager.com",
    "google-analytics.com",
    "mc.yandex.ru",
    "window.datalayer",
    "gtag(",
    "ym(",
)

def visible_text(source):
    source = SCRIPT_RE.sub("", source)
    source = STYLE_RE.sub("", source)
    source = TAG_RE.sub(" ", source)
    return " ".join(html.unescape(source).split())

def protected_seo(source):
    protected = []
    protected.extend(TITLE_RE.findall(source))
    for block in META_RE.findall(source):
        low = block.lower()
        if "description" in low or "og:" in low or "twitter:" in low:
            protected.append(block)
    for block in LINK_RE.findall(source):
        if "canonical" in block.lower():
            protected.append(block)
    for block in SCRIPT_RE.findall(source):
        if "application/ld+json" in block.lower():
            protected.append(block)
    return protected

def analytics_counts(source):
    low = source.lower()
    return {signal: low.count(signal) for signal in ANALYTICS_SIGNALS}

def exact_document_boundaries(source, path):
    checks = {
        "html_open": r"<html(?:\s|>)",
        "html_close": r"</html\s*>",
        "head_open": r"<head(?:\s|>)",
        "head_close": r"</head\s*>",
        "body_open": r"<body(?:\s|>)",
        "body_close": r"</body\s*>",
    }
    for name, pattern in checks.items():
        count = len(re.findall(pattern, source, re.I))
        assert count == 1, f"{path}: {name} count is {count}, expected 1"

def remove_ghost_elements(source, counters):
    def script_callback(match):
        block = match.group(0)
        low = block.lower()
        if any(signal in low for signal in GHOST_SCRIPT_SIGNALS):
            counters["ghost_scripts"] += 1
            return ""
        return block

    def link_callback(match):
        block = match.group(0)
        low = block.lower()
        if any(signal in low for signal in GHOST_LINK_SIGNALS):
            counters["ghost_links"] += 1
            return ""
        return block

    def meta_callback(match):
        block = match.group(0)
        low = block.lower()
        if "generator" in low and "ghost" in low:
            counters["ghost_generator_meta"] += 1
            return ""
        return block

    source = SCRIPT_RE.sub(script_callback, source)
    source = LINK_RE.sub(link_callback, source)
    source = META_RE.sub(meta_callback, source)
    return source

def relative_internal_anchors(source, counters):
    def anchor_callback(anchor_match):
        anchor = anchor_match.group(0)

        def href_callback(href_match):
            prefix, quote, value = href_match.groups()
            parsed = urlsplit(value)
            host = (parsed.hostname or "").lower()
            if host not in {"numerologpro.ru", "www.numerologpro.ru"}:
                return href_match.group(0)
            if parsed.scheme not in {"http", "https", ""}:
                return href_match.group(0)
            path = parsed.path or "/"
            relative = path
            if parsed.query:
                relative += "?" + parsed.query
            if parsed.fragment:
                relative += "#" + parsed.fragment
            counters["relative_internal_links"] += 1
            return prefix + quote + relative + quote

        return HREF_RE.sub(href_callback, anchor)

    return A_OPEN_RE.sub(anchor_callback, source)

def absolute_internal_anchors(source):
    found = []
    for anchor in A_OPEN_RE.findall(source):
        match = HREF_RE.search(anchor)
        if not match:
            continue
        value = match.group(3)
        parsed = urlsplit(value)
        host = (parsed.hostname or "").lower()
        if host in {"numerologpro.ru", "www.numerologpro.ru"}:
            found.append(value)
    return found

def update_agents(source):
    anchor = "## Факты и предположения"
    heading = "## SEO, аналитика и внутренние ссылки"
    rules = [
        "- Рабочие production-настройки Яндекс Метрики и Google Analytics сохраняются при статической миграции; их удаление возможно только по отдельному явному решению пользователя.",
        "- SEO-данные сохраняются: title, description, canonical, Open Graph, Twitter Card и Schema.org/JSON-LD.",
        "- Обычные внутренние навигационные ссылки на `numerologpro.ru` преобразуются в корневые относительные пути, например `/elyor/`; canonical, Open Graph и другие SEO URL остаются абсолютными.",
        "- CSS и JavaScript исходной темы удаляются только после подтверждения, что конкретный код не используется обязательными страницами и его удаление не меняет визуальное или функциональное поведение.",
        "- Проверки границ HTML-документа должны распознавать точные теги; запрещено считать `<header>` совпадением с `<head>`.",
    ]
    assert source.count(anchor) == 1, "AGENTS.md: facts anchor missing or duplicated"
    assert source.count(heading) == 0, "AGENTS.md: SEO section already exists"
    assert "## Точность статической миграции" in source, "AGENTS.md: migration accuracy section missing"
    block = heading + "\n\n" + "\n".join(rules) + "\n\n"
    return source.replace(anchor, block + anchor)

prepared = {}
report = {}

for path in FILES:
    original = path.read_text(encoding="utf-8")
    exact_document_boundaries(original, path)
    before_visible = visible_text(original)
    before_seo = protected_seo(original)
    before_analytics = analytics_counts(original)
    counters = {
        "ghost_scripts": 0,
        "ghost_links": 0,
        "ghost_generator_meta": 0,
        "relative_internal_links": 0,
    }
    cleaned = remove_ghost_elements(original, counters)
    cleaned = relative_internal_anchors(cleaned, counters)
    exact_document_boundaries(cleaned, path)
    assert visible_text(cleaned) == before_visible, f"{path}: visible text changed"
    assert protected_seo(cleaned) == before_seo, f"{path}: protected SEO changed"
    assert analytics_counts(cleaned) == before_analytics, f"{path}: analytics changed"
    leftovers = absolute_internal_anchors(cleaned)
    assert not leftovers, f"{path}: absolute internal anchors remain: {leftovers}"
    low = cleaned.lower()
    ghost_leftovers = []
    for signal in GHOST_SCRIPT_SIGNALS + GHOST_LINK_SIGNALS:
        if signal in low:
            ghost_leftovers.append(signal)
    assert not ghost_leftovers, f"{path}: Ghost runtime remains: {sorted(set(ghost_leftovers))}"
    prepared[path] = cleaned
    report[str(path)] = {
        "before_bytes": len(original.encode("utf-8")),
        "after_bytes": len(cleaned.encode("utf-8")),
        "analytics": before_analytics,
        "changes": counters,
    }

assert sum(item["changes"]["ghost_scripts"] for item in report.values()) > 0, "no Ghost scripts identified"
assert sum(item["changes"]["relative_internal_links"] for item in report.values()) > 0, "no internal links converted"

agents_original = AGENTS.read_text(encoding="utf-8")
agents_updated = update_agents(agents_original)
assert agents_updated.endswith("\n") and not agents_updated.endswith("\n\n")

for path, content in prepared.items():
    path.write_text(content, encoding="utf-8", newline="\n")

AGENTS.write_text(agents_updated, encoding="utf-8", newline="\n")
Path(".work/ghost-clean-report.json").write_text(
    json.dumps(report, ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8",
    newline="\n",
)
print(json.dumps(report, ensure_ascii=False, indent=2))
