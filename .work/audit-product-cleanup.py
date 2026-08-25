from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse
import re

ROOT = Path(".")
PAGES = [
    ("quantocode", ROOT / "quantocode/index.html"),
    ("oracle", ROOT / "oracle/index.html"),
    ("elyor", ROOT / "elyor/index.html"),
]
REPORT = ROOT / "migration-audit/product-cleanup-inputs.md"
WORKLOG = ROOT / "docs/WORKLOG.md"

class AuditParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.records = []
        self.resources = []
        self.classes = []
        self.current = None

    def handle_starttag(self, tag, attrs):
        data = dict(attrs)
        self.stack.append(tag)
        class_value = data.get("class", "")
        if class_value:
            self.classes.extend(class_value.split())

        if tag in {"link", "script", "img"}:
            value = data.get("href") or data.get("src")
            if value:
                self.resources.append((tag, value))

        if tag in {"title", "h1", "h2", "h3", "a"}:
            self.current = {
                "tag": tag,
                "text": [],
                "href": data.get("href", ""),
                "class": class_value,
            }

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_data(self, data):
        if self.current is not None:
            self.current["text"].append(data)

    def handle_endtag(self, tag):
        if self.current is not None and self.current["tag"] == tag:
            self.current["text"] = " ".join("".join(self.current["text"]).split())
            self.records.append(self.current)
            self.current = None
        if self.stack:
            for index in range(len(self.stack) - 1, -1, -1):
                if self.stack[index] == tag:
                    del self.stack[index:]
                    break

def unique(items):
    result = []
    seen = set()
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result

def safe_line(value):
    return value.replace("\r", " ").replace("\n", " ").strip()

def finish(text):
    return text.rstrip("\r\n") + "\n"

lines = [
    "# Product cleanup inputs",
    "",
    "Source checkpoint: `d3e8e4977977719f8648d1a8ba9c712905a1ae32`.",
    "",
    "This report records public runtime references and visible product structure required for the Ghost-free rebuild.",
    "It does not contain raw analytics code, cookies, credentials, authorization headers or infrastructure data.",
]

total_ghost = 0
total_legacy = 0
total_inline_styles = 0
total_inline_scripts = 0

for slug, path in PAGES:
    text = path.read_text(encoding="utf-8")
    parser = AuditParser()
    parser.feed(text)

    headings = [
        record for record in parser.records
        if record["tag"] in {"h1", "h2", "h3"} and record["text"]
    ]
    telegram = unique([
        (record["href"], record["text"], record["class"])
        for record in parser.records
        if record["tag"] == "a"
        and re.search(r"https?://(?:t\.me|telegram\.me)/", record["href"], re.I)
    ])
    resources = unique(parser.resources)
    external_hosts = unique([
        urlparse(value).netloc.lower()
        for tag, value in resources
        if value.startswith(("http://", "https://"))
    ])
    ghost_classes = sorted({
        value for value in parser.classes
        if value.startswith(("gh-", "kg-"))
    })

    ghost_markers = len(re.findall(r"(?i)ghost|gh-|kg-|members|portal|comments", text))
    legacy_refs = text.count("legacy-product.css")
    inline_styles = len(re.findall(r"<style(?:\\s|>)", text, re.I))
    inline_scripts = len(re.findall(r"<script(?![^>]*\\bsrc=)[^>]*>", text, re.I))
    unicode_dashes = sum(text.count(char) for char in ["—", "–", "‑", "−"])

    commercial_patterns = [
        "Telegram Stars",
        "прозрачной цене",
        "цена",
        "оплата",
        "купить",
        "тариф",
    ]
    commercial_hits = [
        (pattern, len(re.findall(re.escape(pattern), text, re.I)))
        for pattern in commercial_patterns
        if re.search(re.escape(pattern), text, re.I)
    ]

    total_ghost += ghost_markers
    total_legacy += legacy_refs
    total_inline_styles += inline_styles
    total_inline_scripts += inline_scripts

    lines.extend(["", f"## /{slug}/", ""])
    titles = [record["text"] for record in parser.records if record["tag"] == "title"]
    lines.append(f"- File size: {len(text.encode(chr(117) + chr(116) + chr(102) + chr(45) + chr(56)))} bytes")
    lines.append(f"- Title: {safe_line(titles[0]) if titles else 'MISSING'}")
    lines.append(f"- Legacy CSS references: {legacy_refs}")
    lines.append(f"- `site.js` references: {text.count('site.js')}")
    lines.append(f"- Inline style blocks: {inline_styles}")
    lines.append(f"- Inline script blocks: {inline_scripts}")
    lines.append(f"- Ghost-related textual markers: {ghost_markers}")
    lines.append(f"- Ghost or card class names: {len(ghost_classes)}")
    lines.append(f"- Unicode dash characters: {unicode_dashes}")
    lines.append(f"- Yandex counter ID occurrences: {text.count('109066888')}")
    lines.append(f"- Google measurement ID occurrences: {text.count('G-EEJ6Z1C216')}")

    lines.extend(["", "### Visible headings", ""])
    if headings:
        for record in headings:
            lines.append(f"- `{record['tag']}` {safe_line(record['text'])}")
    else:
        lines.append("- MISSING")

    lines.extend(["", "### Telegram links", ""])
    if telegram:
        for href, label, class_value in telegram:
            shown_label = safe_line(label) or "[no visible label]"
            shown_class = safe_line(class_value) or "[no class]"
            lines.append(f"- `{href}` - label: `{shown_label}` - class: `{shown_class}`")
    else:
        lines.append("- MISSING")

    lines.extend(["", "### Runtime resources", ""])
    for tag, value in resources:
        lines.append(f"- `{tag}` `{value}`")

    lines.extend(["", "### External resource hosts", ""])
    if external_hosts:
        for host in external_hosts:
            lines.append(f"- `{host}`")
    else:
        lines.append("- None")

    lines.extend(["", "### Commercial-content matches", ""])
    if commercial_hits:
        for pattern, count in commercial_hits:
            lines.append(f"- `{pattern}`: {count}")
    else:
        lines.append("- None")

    lines.extend(["", "### Ghost class sample", ""])
    if ghost_classes:
        for value in ghost_classes[:40]:
            lines.append(f"- `{value}`")
        if len(ghost_classes) > 40:
            lines.append(f"- Remaining class names not listed: {len(ghost_classes) - 40}")
    else:
        lines.append("- None")

lines.extend([
    "",
    "## Combined gate",
    "",
    f"- Ghost-related textual markers: {total_ghost}",
    f"- Legacy CSS references: {total_legacy}",
    f"- Inline style blocks: {total_inline_styles}",
    f"- Inline script blocks: {total_inline_scripts}",
    "- Target after rebuild: zero legacy CSS references, zero Ghost classes and no embedded product design-system CSS.",
    "- Confirmed analytics IDs must remain unchanged during the rebuild.",
])

report = finish("\n".join(lines))
REPORT.parent.mkdir(parents=True, exist_ok=True)
REPORT.write_text(report, encoding="utf-8", newline="\n")

worklog = WORKLOG.read_text(encoding="utf-8")
entry = """
## 25.08.2026 - Checkpoint входных данных очистки продуктовых страниц

- В `migration-audit/product-cleanup-inputs.md` зафиксированы текущие заголовки, Telegram CTA и runtime-ресурсы трёх продуктовых страниц.
- Зафиксированы количества Ghost-маркеров, inline CSS/JS, ссылок на временный `legacy-product.css` и коммерческих формулировок.
- Сырые HTML, код аналитики, cookies, credentials и инфраструктурные данные в отчёт не копировались.
- Опубликованные HTML, CSS и JavaScript на этом шаге не изменялись.
- Следующий шаг: пересобрать `/quantocode/` на семантическом HTML и общей дизайн-системе, сохранив подтверждённый CTA, SEO и аналитику.
"""
WORKLOG.write_text(finish(worklog) + "\n" + finish(entry), encoding="utf-8", newline="\n")

read_back = REPORT.read_text(encoding="utf-8")
assert read_back == report, "Read-back отчёта не совпал"
assert "authorization:" not in read_back.lower()
assert "cookie:" not in read_back.lower()
assert "private key" not in read_back.lower()
assert total_legacy == 6, f"Ожидалось 6 ссылок legacy CSS, найдено {total_legacy}"
assert all(f"## /{slug}/" in read_back for slug, path in PAGES)
print("AUDIT_OK")
print(f"Ghost markers: {total_ghost}")
print(f"Legacy CSS refs: {total_legacy}")
print(f"Inline style blocks: {total_inline_styles}")
print(f"Inline script blocks: {total_inline_scripts}")
