## 1. Resolver: чистые helper'ы аудио/субтитров (xbmc-free)

- [x] 1.1 Добавить чистый helper `resolver.audio_languages(info)`: уникальные языки аудио-only форматов (есть `acodec`, нет видео-кодека) из поля `language`, упорядоченные; проверить детерминированным desktop-тестом `tests/test_resolver_audio_subtitles.py` (фейковые `formats`, без сети): `python3 tests/test_resolver_audio_subtitles.py`
- [x] 1.2 Добавить чистый helper `resolver.original_audio_language(info)`: язык «оригинальной» дорожки по маркерам `format_note` (`original` / `(default)`, регистронезависимо), fallback — единственная языковая дорожка, иначе `None`; проверить кейсами в `tests/test_resolver_audio_subtitles.py` (русский оригинал + англ. auto; без маркеров; без дорожек)
- [x] 1.3 Добавить чистый helper `resolver.subtitle_languages(info)`: языки из объединения `subtitles` и `automatic_captions`; проверить кейсом в `tests/test_resolver_audio_subtitles.py`
- [x] 1.4 Добавить чистый helper `resolver.subtitle_url(info, lang)`: URL записи для языка, предпочитая `ext == "vtt"`, затем `srv3`, пропуская `json3`; проверить кейсами в `tests/test_resolver_audio_subtitles.py` (vtt есть; только json3 -> None)
- [x] 1.5 Добавить чистый helper `resolver.playable_subtitle_urls(info, lang=None)`: список URL субтитров, которые можно привязать к плееру (по языку или первому доступному); проверить в `tests/test_resolver_audio_subtitles.py`

## 2. Настройки по умолчанию

- [x] 2.1 В `resources/settings.xml` добавить `default_audio` (`select`: Auto|Original|ru|en-US|uk|de|fr|es|it|pt-BR|ja|ko|zh-Hans|…`) и `subtitles` (`select`: Off|On) в секции Video; проверить, что XML корректный и подхватывается Kodi (см. п. 3 shim)
- [x] 2.2 В `default.py` добавить чтение настроек в чистые значения: `(audio_mode, audio_lang)` из `default_audio` (Auto -> режим без языка; Original -> язык оригинала по `info`; иначе — тег языка) и `subtitles_default` (bool) из `subtitles`; проверить через расширенный shim-тест, имитирующий `Addon().getSetting`

## 3. Router/UI: применение при старте воспроизведения

- [x] 3.1 В `default.py::play_stream` для HLS применять предпочтение аудио из настроек: Auto — без изменений; Original/язык — применить рабочий на реальном Kodi механизм (см. spike 4.1); при недоступности запрошенной дорожки оставлять выбор плеера и не прерывать воспроизведение; проверить shim-тестом: для Auto никаких изменений, для явного языка — наличие ожидаемого механизма/свойства
- [x] 3.2 В `default.py::play_stream` привязывать субтитры: при `subtitles=On` и наличии дорожек — через `ListItem.setSubtitles`/эквивалент, выбранные URL из `resolver.playable_subtitle_urls`; при `Off` — не форсировать; при отсутствии дорожек — не привязывать; проверить shim-тестом: URL субтитров присутствуют при On и доступных дорожках, отсутствуют при Off/без дорожек
- [x] 3.3 Убедиться, что прогрессивный путь и существующие quality-пути (`play`, прямой `?video_id=..`, `play_quality`) не ломаются: аудио/субтитры применяются поверх уже выбранного потока; проверить `python3 tests/test_desktop.py` и существующие shim-тесты
- [x] 3.4 Обновить docstring роутера `default.py` (упоминание новых настроек) и прогнать `python3 tests/test_kodi_shim.py && python3 tests/test_kodi_shim_list.py && python3 tests/test_kodi_shim_quality.py`

## 4. Интеграция и runtime-верификация на реальном Kodi

- [x] 4.1 Spike на реальном Kodi: определить рабочий механизм принудительного выбора аудио-языка (настройка плеера против свойства ListItem для конкретной версии ISA) и способ включения субтитров по умолчанию; зафиксировать результат в design.md (обновить D2/D4) — до финализации 3.1/3.2
- [x] 4.2 Прогнать весь desktop/shim набор зелёным: `python3 tests/test_resolver_quality.py && python3 tests/test_resolver_audio_subtitles.py && python3 tests/test_desktop.py && python3 tests/test_kodi_shim.py && python3 tests/test_kodi_shim_list.py && python3 tests/test_kodi_shim_quality.py`
- [x] 4.3 На реальном Kodi 21 (Omega) проверить: видео с русским оригиналом и англ. сгенерированной дорожкой при `default_audio=Original` стартует с русским звуком; при `subtitles=On` субтитры видны, при `Off` — нет (и включаются вручную); зафиксировать результат (см. риски design.md)
