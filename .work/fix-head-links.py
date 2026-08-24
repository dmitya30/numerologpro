from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit
import html
import json
import re

FILES = {
    Path("index.html"): "https://numerologpro.ru/",
    Path("elyor/index.html"): "https://numerologpro.ru/elyor/",
    Path("quantocode/index.html"): "https://numerologpro.ru/quantocode/",
    Path("oracle/index.html"): "https://numerologpro.ru/oracle/",
}

FAVICON_ABSOLUTE = "https://numerologpro.ru/content/images/size/w256h256/format/png/2026/05/favicon.svg"
FAVICON_RELATIVE = "/content/images/size/w256h256/format/png/2026/05/favicon.svg"
RSS_URL = "https://numerologpro.ru/blog/rss/"
LINK_TAG = re.compile(r"<link\b[^>]*>", re.I | re.S)
DOUBLE_ATTRIBUTE = re.compile(r"([^\s=/>]+)\s*=\s*\"([^\"]*)\"", re.S)
SCRIPT_BLOCK = re.compile(r"<script\b[^>]*>.*?</script\s*>", re.I | re.S)
STYLE_BLOCK = re.compile(r"<style\b[^>]*>.*?</style\s*>", re.I | re.S)
ANY_TAG = re.compile(r"<[^>]+>", re.S)

def attributes(tag):
    return {match.group(1).lower(): match.group(2) for match in DOUBLE_ATTRIBUTE.finditer(tag)}

def visible_text(source):
    source = SCRIPT_BLOCK.sub("", source)
    source = STYLE_BLOCK.sub("", source)
    source = ANY_TAG.sub(" ", source)
    return " ".join(html.unescape(source).split())

def analytics_counts(source):
    lowered = source.lower()
    markers = ("googletagmanager.com", "mc.yandex.ru")
    return {marker: lowered.count(marker) for marker in markers}

class VerificationParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.icons = []
        self.canonicals = []
        self.rss = []
        self.absolute_internal_anchors = []

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag.lower() == "link":
            rel = set((values.get("rel") or "").lower().split())
            href = values.get("href") or ""
            if "icon" in rel:
                self.icons.append(href)
            if "canonical" in rel:
                self.canonicals.append(href)
            if "alternate" in rel and href == RSS_URL:
                self.rss.append(href)
        if tag.lower() == "a":
            href = values.get("href") or ""
            parsed = urlsplit(href)
            host = (parsed.hostname or "").lower()
            if host in {"numerologpro.ru", "www.numerologpro.ru"}:
                self.absolute_internal_anchors.append(href)

def transform(source, path):
    counters = {"favicon_links_changed": 0, "rss_links_removed": 0}

    def callback(match):
        tag = match.group(0)
        values = attributes(tag)
        rel = set(values.get("rel", "").lower().split())
        href = values.get("href", "")

        if "icon" in rel and href == FAVICON_ABSOLUTE:
            counters["favicon_links_changed"] += 1
            return tag.replace(FAVICON_ABSOLUTE, FAVICON_RELATIVE, 1)

        if "alternate" in rel and href == RSS_URL:
            counters["rss_links_removed"] += 1
            return ""

        return tag

    result = LINK_TAG.sub(callback, source)
    assert counters["favicon_links_changed"] == 1, f"{path}: changed icon links {counters["favicon_links_changed"]}, expected 1"
    assert counters["rss_links_removed"] == 1, f"{path}: removed RSS links {counters["rss_links_removed"]}, expected 1"
    return result, counters

prepared = {}
report = {}

for path, expected_canonical in FILES.items():
    original = path.read_text(encoding="utf-8")
    before_text = visible_text(original)
    before_analytics = analytics_counts(original)
    result, counters = transform(original, path)

    parser = VerificationParser()
    parser.feed(result)
    parser.close()

    assert parser.icons == [FAVICON_RELATIVE], f"{path}: icon links are {parser.icons}"
    assert parser.canonicals == [expected_canonical], f"{path}: canonical links are {parser.canonicals}"
    assert not parser.rss, f"{path}: RSS link remains"
    assert not parser.absolute_internal_anchors, f"{path}: absolute navigation remains: {parser.absolute_internal_anchors}"
    assert visible_text(result) == before_text, f"{path}: visible text changed"
    assert analytics_counts(result) == before_analytics, f"{path}: analytics changed"
    assert result.count(FAVICON_ABSOLUTE) == original.count(FAVICON_ABSOLUTE) - 1, f"{path}: unexpected favicon URL change"
    assert result.count(FAVICON_RELATIVE) == 1, f"{path}: relative favicon count is not 1"

    prepared[path] = result
    report[str(path)] = {
        "favicon_absolute_before": original.count(FAVICON_ABSOLUTE),
        "favicon_absolute_after": result.count(FAVICON_ABSOLUTE),
        "favicon_link": parser.icons[0],
        "canonical": parser.canonicals[0],
        "analytics": before_analytics,
        "changes": counters,
    }

for path, result in prepared.items():
    path.write_text(result, encoding="utf-8", newline="\n")

Path(".work/head-clean-report.json").write_text(
    json.dumps(report, ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8",
    newline="\n",
)

print(json.dumps(report, ensure_ascii=False, indent=2))
