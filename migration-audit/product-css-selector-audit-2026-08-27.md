# Product CSS selector audit - 27.08.2026

Source checkpoint: `568fc7045524d0268423c0ed2a9c4c956ce6f7bc`.

Аудит сопоставил selector tokens трёх product-specific CSS с фактическим статическим DOM соответствующих HTML-страниц.

## Результат очистки

### quantocode

- CSS bytes до очистки: 21424.
- CSS bytes после очистки: 14380.
- Удалено selector branches: 50.
- Полностью удалено rules: 37.
- Частично переписано смешанных rules: 4.
- Удалено legacy-комментариев: 4.

### oracle

- CSS bytes до очистки: 24882.
- CSS bytes после очистки: 17711.
- Удалено selector branches: 50.
- Полностью удалено rules: 37.
- Частично переписано смешанных rules: 4.
- Удалено legacy-комментариев: 4.

### elyor

- CSS bytes до очистки: 21102.
- CSS bytes после очистки: 14064.
- Удалено selector branches: 50.
- Полностью удалено rules: 37.
- Частично переписано смешанных rules: 4.
- Удалено legacy-комментариев: 4.

## Границы решения

- Удалялись только ветви с отсутствующими static DOM tokens.
- Активные global element selectors и CSS variables не удалялись.
- JavaScript не добавляет проверяемые legacy classes во время runtime.
- Внешний вид требует повторного desktop и mobile QA после публикации.

## Следующий шаг

Проверить оставшиеся глобальные правила и custom properties отдельно, не смешивая это с текущим доказанным удалением.

## Дополнительная верификация 28.08.2026

- Первый cleanup-парсер не удалил часть вложенных и смешанных legacy selectors.
- Остаточные `dark-mode`, `nav-current`, `site-main`, theme-button и `body.page-*` rules удалены отдельным checkpoint.
- После удаления проверены обязательные активные product wrapper selectors и баланс CSS braces.
- Визуальный QA первого cleanup: PASS.
