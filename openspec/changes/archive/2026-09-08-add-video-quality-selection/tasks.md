## 1. Resolver: перечисление и выбор качества (xbmc-free)

- [x] 1.1 Добавить чистый helper `resolver.available_heights(info)`: уникальные высоты из `formats` с видеокодеком, отсортированные по убыванию; проверить новым детерминированным desktop-тестом `tests/test_resolver_quality.py` (фейковые `formats`, без сети): `python3 tests/test_resolver_quality.py`
- [x] 1.2 Добавить чистый helper форматирования `resolver.height_label(h)` -> `"720p"` и т.п.; проверить в `tests/test_resolver_quality.py` (кейсы для 144/240/360/480/720/1080/1440/2160)
- [x] 1.3 Расширить `resolver.pick_progressive(info, max_height=None)`: при заданном `max_height` выбирать лучший muxed-формат с `height <= max_height`, без него — прежнее поведение; проверить кейсом в `tests/test_resolver_quality.py` + убедиться, что `python3 tests/test_desktop.py` по-прежнему проходит
- [x] 1.4 Расширить `resolver.resolve_video(url, allow_progressive=True, max_height=None)`: пробрасывать `max_height` в прогрессивный fallback (HLS-путь не меняет URL — cap применяется на уровне UI); проверить, что `python3 tests/test_desktop.py` и `tests/test_resolver_quality.py` проходят

## 2. Настройка «Качество по умолчанию»

- [x] 2.1 Создать `resources/settings.xml` с пунктом «Default video quality» (Auto/Best + 144p…2160p) в секции video; проверить, что файл корректный XML и подхватывается Kodi (значения: `0` = Auto/Best, иначе высота)
- [x] 2.2 В `default.py` добавить чтение настройки в высоту/cap (`0`/пусто -> `None` = Auto/Best); проверить через расширенный shim-тест, имитирующий `Addon().getSetting` (см. п. 3)

## 3. Router/UI: выбор качества перед воспроизведением

- [x] 3.1 В `default.py::add_video` добавить пункт контекстного меню «Play with quality…» на каждый видео-элемент, ведущий на `play_quality?video_id=..`; проверить, что `python3 tests/test_kodi_shim_list.py` подтверждает наличие контекстного пункта с корректным URL
- [x] 3.2 Добавить ветку роутера `play_quality`: один резолв, список качеств = `[Auto/Best] + available_heights`, выбор через `xbmcgui.Dialog().select`, затем запуск воспроизведения с выбранным cap; проверить расширенным shim-тестом: имитация выбора в диалоге -> `setResolvedUrl(True, item)`
- [x] 3.3 В `play_video` принимать параметр качества (из URL `quality=<height>` либо из настройки по умолчанию) и применять: для HLS выставлять свойство ListItem `inputstream.adaptive.max_resolution`, для прогрессива передавать `max_height` в `resolver.resolve_video`; для Auto/Best свойство НЕ выставлять; проверить shim-тестом: при cap='720' свойство присутствует и равно '720', при Auto — отсутствует
- [x] 3.4 Убедиться, что «обычный» клик (`play` и прямой `?video_id=..`) не открывает диалог и применяет настройку по умолчанию; проверить shim-тестом с настройкой по умолчанию `1080`
- [x] 3.5 Обновить docstring роутера `default.py` (новые action-параметры) и убедиться, что `python3 tests/test_kodi_shim.py` и `python3 tests/test_kodi_shim_list.py` проходят

## 4. Интеграционная проверка

- [x] 4.1 Прогнать весь desktop/shim набор и убедиться в зелёном результате: `python3 tests/test_resolver_quality.py && python3 tests/test_desktop.py && python3 tests/test_kodi_shim.py && python3 tests/test_kodi_shim_list.py`
- [ ] 4.2 Проверить на реальном Kodi 21 (Omega), что выбранный cap реально ограничивает разрешение воспроизведения (свойство `inputstream.adaptive.max_resolution` учитывается ISA): включить видео через «Play with quality…», выбрать 360p и наблюдать разрешение ≤ 360p; зафиксировать результат (см. риск в design.md)
