# Static baseline audit - 27.08.2026

Source checkpoint: `8682cebb672d575106c6d9851a8c5dff43095943`.

Этот отчёт фиксирует текущее санитизированное состояние статического baseline. Исторические отчёты в этом каталоге описывают более ранние migration checkpoints и не являются списком текущего runtime.

## Scope

- `/`
- `/elyor/`
- `/quantocode/`
- `/oracle/`
- `404.html`
- общие CSS, JavaScript, fonts, images, metadata, robots.txt и sitemap.xml

## Подтверждено

- Все четыре обязательных маршрута присутствуют в публикуемой ветке.
- Canonical URL указывают на production-маршруты `https://numerologpro.ru/`.
- Social image URL и Schema.org logo являются абсолютными production URL.
- Яндекс Метрика `109066888` и Google Analytics `G-EEJ6Z1C216` сохранены.
- Главная и 404 содержат полный GA bootstrap; product pages не получили его дублей.
- Telegram CTA сохранены на всех product pages.
- Явные цены, способы оплаты и ссылки на исключённые юридические маршруты удалены.
- Ошибочные Quantocode Organization и WebSite Schema.org-блоки удалены из Oracle и ЭЛИОР.
- Lora Roman, Lora Italic и Inter загружаются из локальных файлов.
- Product header использует sticky positioning.
- `.work/` отсутствует в публикуемом Git-дереве и игнорируется.
- robots.txt указывает на production sitemap; sitemap содержит четыре обязательных URL.

## Остаётся проверить

- Фактическое использование каждого селектора в трёх product-specific CSS-файлах.
- Возможность удаления исторических Source theme overrides и legacy-комментариев без изменения UI.
- Browser console и network на desktop и mobile.
- Keyboard focus, horizontal scroll и поведение sticky header на поддерживаемых viewport.
- Отсутствие неожиданных запросов к Ghost и VPS во время browser-level QA.
- Итоговое поведение `/about/` и остальных legacy URL.

## Следующий безопасный шаг

Выполнить read-only сопоставление product CSS selectors с фактическим DOM. До получения отчёта CSS не удалять.
