#!/usr/bin/env python3
"""Verify the static NumerologPro publication baseline."""

from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit
import json
import re
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
GA_ID = "G-EEJ6Z1C216"
YM_ID = "109066888"

PAGES = {
    "index.html": {
        "canonical": "https://numerologpro.ru/",
        "telegram": None,
    },
    "quantocode/index.html": {
        "canonical": "https://numerologpro.ru/quantocode/",
        "telegram": "telegram.me/quantocode_bot",
    },
    "oracle/index.html": {
        "canonical": "https://numerologpro.ru/oracle/",
        "telegram": "telegram.me/mistic_oracle_bot",
    },
    "elyor/index.html": {
        "canonical": "https://numerologpro.ru/elyor/",
        "telegram": "telegram.me/yourElyor_bot",
    },
    "about/index.html": {
        "canonical": "https://numerologpro.ru/about/",
        "telegram": "telegram.me/quantocode_bot",
    },
    "404.html": {
        "canonical": None,
        "telegram": None,
    },
}

EXPECTED_SITEMAP = {
    "https://numerologpro.ru/",
    "https://numerologpro.ru/elyor/",
    "https://numerologpro.ru/quantocode/",
    "https://numerologpro.ru/oracle/",
    "https://numerologpro.ru/about/",
}

GHOST_MARKERS = [
    "ghost/api",
    "/ghost/",
    "portal.min.js",
    "search.min.js",
    "comment-count",
    "data-ghost",
    "members/api",
]

THEME_MARKERS = [
    "prefers-color-scheme",
    "dark-mode",
    "theme-toggle",
    "data-theme",
]

COMMERCIAL_MARKERS = [
    "telegram stars",
    "оплата",
    "тариф",
    "купить",
    "₽",
]

EXCLUDED_ROUTES = [
    "privacy/",
    "consent/",
    "oferta/",
]

class PageParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.refs = []
        self.anchors = []
        self.ids = set()
        self.canonicals = []
        self.descriptions = []
        self.og_images = []
        self.twitter_images = []
        self.json_ld = []
        self.title_count = 0
        self.html_count = 0
        self.head_count = 0
        self.body_count = 0
        self.current_json_ld = False
        self.json_buffer = []

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        tag = tag.lower()
        if tag == "html":
            self.html_count += 1
        elif tag == "head":
            self.head_count += 1
        elif tag == "body":
            self.body_count += 1
        elif tag == "title":
            self.title_count += 1

        element_id = values.get("id")
        if element_id:
            self.ids.add(element_id)

        if tag == "a" and values.get("href"):
            self.anchors.append(values["href"])

        if tag == "link" and values.get("href"):
            self.refs.append(values["href"])
            rel = values.get("rel", "").lower().split()
            if "canonical" in rel:
                self.canonicals.append(values["href"])

        if tag in {"script", "img", "source"}:
            if values.get("src"):
                self.refs.append(values["src"])
            if values.get("srcset"):
                for item in values["srcset"].split(","):
                    candidate = item.strip().split()[0]
                    if candidate:
                        self.refs.append(candidate)

        if tag == "meta":
            key = values.get("name") or values.get("property") or ""
            content = values.get("content", "")
            if key == "description":
                self.descriptions.append(content)
            elif key == "og:image":
                self.og_images.append(content)
            elif key == "twitter:image":
                self.twitter_images.append(content)

        if tag == "script" and values.get("type") == "application/ld+json":
            self.current_json_ld = True
            self.json_buffer = []

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)

    def handle_data(self, data):
        if self.current_json_ld:
            self.json_buffer.append(data)

    def handle_endtag(self, tag):
        if tag.lower() == "script" and self.current_json_ld:
            self.json_ld.append("".join(self.json_buffer))
            self.current_json_ld = False
            self.json_buffer = []

errors = []
checks = 0

def require(condition, message):
    global checks
    checks += 1
    if not condition:
        errors.append(message)

def local_target(page_path, value):
    parsed = urlsplit(value)
    if parsed.scheme or parsed.netloc or value.startswith("//"):
        return None
    if not parsed.path or parsed.path.startswith("#"):
        return None
    path_text = unquote(parsed.path)
    if path_text.startswith("/"):
        candidate = ROOT / path_text.lstrip("/")
    else:
        candidate = page_path.parent / path_text
    candidate = candidate.resolve()
    try:
        candidate.relative_to(ROOT.resolve())
    except ValueError:
        return candidate
    if candidate.is_dir():
        candidate = candidate / "index.html"
    return candidate

for relative, config in PAGES.items():
    path = ROOT / relative
    require(path.is_file(), relative + ": page file is missing")
    if not path.is_file():
        continue

    text = path.read_text(encoding="utf-8")
    lower = text.lower()
    parser = PageParser()
    parser.feed(text)

    require(parser.html_count == 1, relative + ": html element count is invalid")
    require(parser.head_count == 1, relative + ": head element count is invalid")
    require(parser.body_count == 1, relative + ": body element count is invalid")
    require(parser.title_count == 1, relative + ": title count is invalid")
    require(GA_ID in text, relative + ": Google Analytics ID is missing")
    require(YM_ID in text, relative + ": Yandex Metrika ID is missing")

    normalized = text.replace(chr(39), chr(34)).replace(" ", "")
    ga_call = "gtag(" + chr(34) + "config" + chr(34) + "," + chr(34) + GA_ID + chr(34) + ")"
    require(ga_call in normalized, relative + ": GA config call is missing")

    canonical = config["canonical"]
    if canonical is None:
        require(not parser.canonicals, relative + ": unexpected canonical")
    else:
        require(parser.canonicals == [canonical], relative + ": canonical is invalid")
        require(len(parser.descriptions) == 1, relative + ": description count is invalid")
        require(parser.og_images == ["https://numerologpro.ru/assets/images/home/og-quiet-house.jpg"], relative + ": og:image is invalid")
        require(parser.twitter_images == ["https://numerologpro.ru/assets/images/home/og-quiet-house.jpg"], relative + ": twitter:image is invalid")

    for block_number, block in enumerate(parser.json_ld, start=1):
        try:
            json.loads(block)
        except json.JSONDecodeError as error:
            errors.append(relative + ": invalid JSON-LD block " + str(block_number) + ": " + str(error))

    for marker in GHOST_MARKERS:
        require(marker not in lower, relative + ": Ghost marker remains: " + marker)

    for marker in THEME_MARKERS:
        require(marker not in lower, relative + ": theme marker remains: " + marker)

    for marker in COMMERCIAL_MARKERS:
        require(marker not in lower, relative + ": commercial marker remains: " + marker)

    for route in EXCLUDED_ROUTES:
        require(route not in parser.anchors, relative + ": excluded route is linked: " + route)

    telegram = config["telegram"]
    if telegram:
        matches = [href for href in parser.anchors if telegram in href]
        require(bool(matches), relative + ": required Telegram CTA is missing")

    for value in parser.refs + parser.anchors:
        if value.startswith("#"):
            fragment = unquote(value[1:])
            if fragment:
                require(fragment in parser.ids, relative + ": missing fragment target #" + fragment)
            continue
        target = local_target(path, value)
        if target is not None:
            require(target.is_file(), relative + ": missing local target for " + value)

css_paths = sorted((ROOT / "assets/css").glob("*.css"))
require(bool(css_paths), "no CSS files found")

for css_path in css_paths:
    css = css_path.read_text(encoding="utf-8")
    lower = css.lower()
    for marker in THEME_MARKERS:
        require(marker not in lower, css_path.relative_to(ROOT).as_posix() + ": theme marker remains: " + marker)
    for raw_url in re.findall(r"url\(([^)]+)\)", css):
        value = raw_url.strip().strip(chr(34)).strip(chr(39))
        if value.startswith("data:") or value.startswith("#"):
            continue
        target = local_target(css_path, value)
        if target is not None:
            require(target.is_file(), css_path.relative_to(ROOT).as_posix() + ": missing CSS resource " + value)

robots = (ROOT / "robots.txt").read_text(encoding="utf-8")
require("User-agent: *" in robots, "robots.txt lacks wildcard user-agent")
require("Allow: /" in robots, "robots.txt lacks Allow directive")
require("Sitemap: https://numerologpro.ru/sitemap.xml" in robots, "robots.txt sitemap is invalid")

tree = ET.parse(ROOT / "sitemap.xml")
namespace = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
urls = {node.text for node in tree.findall("sm:url/sm:loc", namespace)}
require(urls == EXPECTED_SITEMAP, "sitemap URL set is invalid")
require(len(tree.findall("sm:url", namespace)) == 5, "sitemap URL count is invalid")

require((ROOT / ".nojekyll").is_file(), ".nojekyll is missing")
require(".work/" in (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines(), ".work is not ignored")

if errors:
    print("STATIC_SITE_INTEGRITY: FAIL")
    for error in errors:
        print("FAIL:", error)
    print("CHECKS:", checks)
    print("ERRORS:", len(errors))
    sys.exit(1)

print("STATIC_SITE_INTEGRITY: PASS")
print("CHECKS:", checks)
print("PAGES:", len(PAGES))
print("CSS FILES:", len(css_paths))
print("SITEMAP URLS:", len(urls))
