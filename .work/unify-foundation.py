from pathlib import Path

root = Path(".")
index_path = root / "index.html"
home_css_path = root / "assets/css/home.css"
lora_css_path = root / "assets/css/lora.css"
site_css_path = root / "assets/css/site.css"
legacy_css_path = root / "assets/css/legacy-product.css"
home_js_path = root / "assets/js/home.js"
site_js_path = root / "assets/js/site.js"
worklog_path = root / "docs/WORKLOG.md"
product_paths = [
    root / "elyor/index.html",
    root / "oracle/index.html",
    root / "quantocode/index.html",
]

def read(path):
    return path.read_text(encoding="utf-8")

def final_newline(text):
    return text.rstrip("\r\n") + "\n"

index = read(index_path)
home_css = read(home_css_path)
lora_css = read(lora_css_path)
legacy_css = read(site_css_path)
home_js = read(home_js_path)
legacy_js = read(site_js_path)
worklog = read(worklog_path)
products = {path: read(path) for path in product_paths}

lora_link = "  <link rel=\"stylesheet\" href=\"assets/css/lora.css\">"
home_link = "  <link rel=\"stylesheet\" href=\"assets/css/home.css\">"
site_link = "  <link rel=\"stylesheet\" href=\"assets/css/site.css\">"
home_script = "  <script src=\"assets/js/home.js\" defer></script>"
site_script = "  <script src=\"assets/js/site.js\" defer></script>"

assert index.count(lora_link) == 1, "Некорректное число ссылок lora.css в index.html"
assert index.count(home_link) == 1, "Некорректное число ссылок home.css в index.html"
assert index.count(home_script) == 1, "Некорректное число ссылок home.js в index.html"
assert legacy_js.count("s=a.querySelector") == 1, "Не найден ожидаемый guard-anchor в site.js"
assert "gh-navigation" not in home_js, "home.js неожиданно содержит Ghost navigation"
assert "gh-navigation" not in home_css, "home.css неожиданно содержит Ghost navigation"

for path, text in products.items():
    assert text.count("../assets/css/site.css") == 2, f"{path}: ожидалось две ссылки site.css"
    assert text.count("../assets/js/site.js") >= 2, f"{path}: не найдены ссылки site.js"

new_index = index.replace(lora_link + "\n" + home_link, site_link)
new_index = new_index.replace(home_script, site_script)

new_site_css = final_newline(final_newline(lora_css) + "\n" + final_newline(home_css))
safe_legacy_js = legacy_js.replace("s=a.querySelector", "s=a?.querySelector", 1)
new_site_js = final_newline(final_newline(home_js) + "\n" + final_newline(safe_legacy_js))

new_products = {}
for path, text in products.items():
    new_products[path] = text.replace("../assets/css/site.css", "../assets/css/legacy-product.css")

entry = """
## 25.08.2026 - Checkpoint единой CSS/JS-основы

- Главная переведена на финальные `assets/css/site.css` и `assets/js/site.js`.
- Локальные правила Lora объединены со стилями главной в `site.css`.
- `home.css`, `lora.css` и `home.js` удалены как отдельные runtime-файлы.
- Прежний Ghost CSS временно сохранён как `legacy-product.css` только для трёх продуктовых страниц.
- Защитная проверка позволяет единому `site.js` работать и на главной без Ghost DOM.
- Контент, аналитика и визуальная композиция страниц на этом шаге не изменялись.
- Следующий шаг: семантическая пересборка и лёгкий редизайн продуктовых страниц без Ghost-классов.
"""
new_worklog = final_newline(worklog) + "\n" + final_newline(entry)

legacy_css_path.write_text(final_newline(legacy_css), encoding="utf-8", newline="\n")
site_css_path.write_text(new_site_css, encoding="utf-8", newline="\n")
site_js_path.write_text(new_site_js, encoding="utf-8", newline="\n")
index_path.write_text(final_newline(new_index), encoding="utf-8", newline="\n")
worklog_path.write_text(new_worklog, encoding="utf-8", newline="\n")

for path, text in new_products.items():
    path.write_text(final_newline(text), encoding="utf-8", newline="\n")

home_css_path.unlink()
lora_css_path.unlink()
home_js_path.unlink()

print("PATCH_OK")
