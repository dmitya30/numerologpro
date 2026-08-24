from __future__ import annotations

import hashlib
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

BASE_URL = "https://numerologpro.ru/"
PAGES = {
    "home": urllib.parse.urljoin(BASE_URL, ""),
    "elyor": urllib.parse.urljoin(BASE_URL, "elyor/"),
    "quantocode": urllib.parse.urljoin(BASE_URL, "quantocode/"),
    "oracle": urllib.parse.urljoin(BASE_URL, "oracle/"),
    "about-review": urllib.parse.urljoin(BASE_URL, "about/"),
}
OUTPUT_ROOT = Path(".work/source-audit")
SNAPSHOT_ROOT = OUTPUT_ROOT / "pages"
REPORT_PATH = OUTPUT_ROOT / "audit.json"
USER_AGENT = "numerologpro-static-migration-audit/1.0"
COMMERCIAL_MARKERS = [
    "₽",
    "руб",
    "купить",
    "тариф",
    "оплата",
    "telegram stars",
    "цена",
    "стоимость",
    "платн",
]
GHOST_MARKERS = [
    "/ghost/",
    "ghost/api/",
    "ghost-portal",
    "members/api/",
    "comments-ui",
    "comment-counts",
    "webmentions",
    "/assets/built/source.js",
    "/assets/built/screen.css",
]


def normalize_space(value: str) -> str:
    return " ".join(value.split())


def css_urls(value: str) -> list[str]:
    found = []
    for candidate in re.findall(r"url\(([^)]+)\)", value, flags=re.IGNORECASE):
        cleaned = candidate.strip().strip(chr(34)).strip(chr(39))
        if cleaned and not cleaned.lower().startswith("data:"):
            found.append(cleaned)
    return found


class PageParser(HTMLParser):
    def __init__(self, page_url: str) -> None:
        super().__init__(convert_charrefs=True)
        self.page_url = page_url
        self.title_parts: list[str] = []
        self.in_title = False
        self.style_depth = 0
        self.meta: dict[str, str] = {}
        self.canonical = ""
        self.links: list[dict[str, str]] = []
        self.assets: set[str] = set()
        self.inline_css_urls: set[str] = set()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {key.lower(): value or "" for key, value in attrs}
        lowered_tag = tag.lower()

        if lowered_tag == "title":
            self.in_title = True

        if lowered_tag == "style":
            self.style_depth += 1

        if lowered_tag == "meta":
            key = values.get("name") or values.get("property")
            content = values.get("content", "")
            if key and content:
                self.meta[key.lower()] = normalize_space(content)

        if lowered_tag == "link":
            href = values.get("href", "")
            rel = values.get("rel", "").lower()
            if href and "canonical" in rel.split():
                self.canonical = urllib.parse.urljoin(self.page_url, href)
            if href and any(item in rel.split() for item in ["stylesheet", "icon", "preload", "manifest"]):
                self.assets.add(urllib.parse.urljoin(self.page_url, href))

        if lowered_tag == "a":
            href = values.get("href", "")
            if href:
                self.links.append(
                    {
                        "href": urllib.parse.urljoin(self.page_url, href),
                        "text": "",
                        "class": values.get("class", ""),
                    }
                )

        source_attributes = {
            "img": ["src"],
            "script": ["src"],
            "source": ["src"],
            "video": ["src", "poster"],
            "audio": ["src"],
            "iframe": ["src"],
        }
        for attribute in source_attributes.get(lowered_tag, []):
            value = values.get(attribute, "")
            if value and not value.lower().startswith("data:"):
                self.assets.add(urllib.parse.urljoin(self.page_url, value))

        srcset = values.get("srcset", "")
        if srcset:
            for candidate in srcset.split(","):
                value = candidate.strip().split(" ")[0]
                if value and not value.lower().startswith("data:"):
                    self.assets.add(urllib.parse.urljoin(self.page_url, value))

        style = values.get("style", "")
        for value in css_urls(style):
            self.inline_css_urls.add(urllib.parse.urljoin(self.page_url, value))

    def handle_endtag(self, tag: str) -> None:
        lowered_tag = tag.lower()
        if lowered_tag == "title":
            self.in_title = False
        if lowered_tag == "style" and self.style_depth:
            self.style_depth -= 1

    def handle_data(self, data: str) -> None:
        if self.in_title:
            self.title_parts.append(data)
        if self.style_depth:
            for value in css_urls(data):
                self.inline_css_urls.add(urllib.parse.urljoin(self.page_url, value))
        if self.links and data.strip():
            current = self.links[-1]
            current["text"] = normalize_space((current["text"] + " " + data).strip())

    def result(self) -> dict[str, object]:
        assets = sorted(self.assets | self.inline_css_urls)
        internal_assets = [value for value in assets if urllib.parse.urlparse(value).netloc == "numerologpro.ru"]
        external_assets = [value for value in assets if urllib.parse.urlparse(value).netloc != "numerologpro.ru"]
        telegram_links = sorted(
            {
                item["href"]
                for item in self.links
                if urllib.parse.urlparse(item["href"]).netloc.lower()
                in {"t.me", "telegram.me", "www.t.me", "www.telegram.me"}
            }
        )
        internal_links = sorted(
            {
                item["href"]
                for item in self.links
                if urllib.parse.urlparse(item["href"]).netloc == "numerologpro.ru"
            }
        )
        external_links = sorted(
            {
                item["href"]
                for item in self.links
                if urllib.parse.urlparse(item["href"]).netloc not in {"", "numerologpro.ru"}
            }
        )
        return {
            "title": normalize_space("".join(self.title_parts)),
            "description": self.meta.get("description", ""),
            "canonical": self.canonical,
            "open_graph": {
                key: value
                for key, value in sorted(self.meta.items())
                if key.startswith("og:")
            },
            "twitter": {
                key: value
                for key, value in sorted(self.meta.items())
                if key.startswith("twitter:")
            },
            "telegram_links": telegram_links,
            "internal_links": internal_links,
            "external_links": external_links,
            "internal_assets": internal_assets,
            "external_assets": external_assets,
        }


def fetch(url: str) -> tuple[int, str, bytes, str]:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            status = response.status
            content_type = response.headers.get("Content-Type", "")
            body = response.read()
            final_url = response.geturl()
            return status, content_type, body, final_url
    except urllib.error.HTTPError as error:
        body = error.read()
        return error.code, error.headers.get("Content-Type", ""), body, error.geturl()


def main() -> int:
    SNAPSHOT_ROOT.mkdir(parents=True, exist_ok=True)
    report: dict[str, object] = {
        "base_url": BASE_URL,
        "pages": {},
    }
    failures: list[str] = []

    for name, url in PAGES.items():
        try:
            status, content_type, body, final_url = fetch(url)
            snapshot_path = SNAPSHOT_ROOT / f"{name}.html"
            snapshot_path.write_bytes(body)
            text = body.decode("utf-8", errors="replace")
            parser = PageParser(final_url)
            parser.feed(text)
            page_report = parser.result()
            lowered = text.lower()
            page_report.update(
                {
                    "requested_url": url,
                    "final_url": final_url,
                    "status": status,
                    "content_type": content_type,
                    "bytes": len(body),
                    "sha256": hashlib.sha256(body).hexdigest(),
                    "commercial_markers": [
                        marker
                        for marker in COMMERCIAL_MARKERS
                        if marker.lower() in lowered
                    ],
                    "ghost_markers": [
                        marker
                        for marker in GHOST_MARKERS
                        if marker.lower() in lowered
                    ],
                }
            )
            report["pages"][name] = page_report
            if status != 200:
                failures.append(f"{name}: HTTP {status}")
        except Exception as error:
            report["pages"][name] = {"requested_url": url, "error": str(error)}
            failures.append(f"{name}: {error}")

    REPORT_PATH.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    for name, page in report["pages"].items():
        print(f"[{name}]")
        if "error" in page:
            print(f"  ERROR: {page["error"]}")
            continue
        print(f"  HTTP: {page["status"]}")
        print(f"  bytes: {page["bytes"]}")
        print(f"  title: {page["title"]}")
        print(f"  canonical: {page["canonical"]}")
        print(f"  Telegram CTA: {len(page["telegram_links"])}")
        for value in page["telegram_links"]:
            print(f"    {value}")
        print(f"  internal assets: {len(page["internal_assets"])}")
        print(f"  external assets: {len(page["external_assets"])}")
        print(f"  commercial markers: {page["commercial_markers"]}")
        print(f"  Ghost markers: {page["ghost_markers"]}")

    print(f"Report: {REPORT_PATH.as_posix()}")
    print(f"Snapshots: {SNAPSHOT_ROOT.as_posix()}")

    if failures:
        print("FAIL: " + "; ".join(failures))
        return 1

    print("PASS: все страницы получены, снимки и audit.json созданы.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
