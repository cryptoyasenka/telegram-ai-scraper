"""Minimal i18n: 3 languages, cookie-based selection."""

LANGUAGES = {"en": "English", "ru": "Русский", "uk": "Українська"}
DEFAULT_LANG = "ru"

_STRINGS = {
    # --- base / nav ---
    "nav_channels": {"en": "Channels", "ru": "Каналы", "uk": "Канали"},
    "nav_search": {"en": "Search", "ru": "Поиск", "uk": "Пошук"},

    # --- index ---
    "channels_title": {"en": "Channels", "ru": "Каналы", "uk": "Канали"},
    "add_placeholder": {"en": "@username or t.me/...", "ru": "@username или t.me/...", "uk": "@username або t.me/..."},
    "add_button": {"en": "Add and scan", "ru": "Добавить и просканировать", "uk": "Додати і просканувати"},
    "active_jobs": {"en": "Active jobs", "ru": "Активные задачи", "uk": "Активні завдання"},
    "th_channel": {"en": "Channel", "ru": "Канал", "uk": "Канал"},
    "th_posts": {"en": "Posts", "ru": "Постов", "uk": "Постів"},
    "th_on_disk": {"en": "Media on disk", "ru": "Медиа на диске", "uk": "Медіа на диску"},
    "th_available": {"en": "Available to download", "ru": "Доступно скачать", "uk": "Доступно завантажити"},
    "open": {"en": "Open", "ru": "Открыть", "uk": "Відкрити"},
    "no_channels": {"en": "No channels yet. Add one above.", "ru": "Пока нет каналов. Добавь через форму выше.", "uk": "Поки немає каналів. Додай через форму вище."},

    # --- channel ---
    "back_channels": {"en": "Channels", "ru": "Каналы", "uk": "Канали"},
    "posts_suffix": {"en": "posts", "ru": "постов", "uk": "постів"},
    "media_suffix": {"en": "media", "ru": "медиа", "uk": "медіа"},
    "update_button": {"en": "Update (new posts + sizes)", "ru": "Обновить (новые посты + размеры)", "uk": "Оновити (нові пости + розміри)"},
    "all_messages": {"en": "All messages", "ru": "Все сообщения", "uk": "Усі повідомлення"},
    "fill_sizes": {"en": "Fill sizes", "ru": "Заполнить размеры", "uk": "Заповнити розміри"},
    "missing_sizes_warn": {
        "en": "%(n)s messages have unknown media size — ETA will be inaccurate until filled.",
        "ru": "У %(n)s сообщений неизвестен размер медиа — ETA будет неточным, пока не заполнишь.",
        "uk": "У %(n)s повідомлень невідомий розмір медіа — ETA буде неточним, поки не заповниш.",
    },
    "download_dir": {"en": "Download folder", "ru": "Папка загрузки", "uk": "Папка завантаження"},
    "custom_hint": {"en": "(custom)", "ru": "(кастомная)", "uk": "(власна)"},
    "browse": {"en": "Browse", "ru": "Обзор", "uk": "Огляд"},
    "fb_up": {"en": "Up", "ru": "Вверх", "uk": "Вгору"},
    "fb_new_folder": {"en": "+ Folder", "ru": "+ Папка", "uk": "+ Папка"},
    "fb_select": {"en": "Select this folder", "ru": "Выбрать эту папку", "uk": "Обрати цю папку"},
    "save": {"en": "Save", "ru": "Сохранить", "uk": "Зберегти"},
    "reset_default": {"en": "Reset to default", "ru": "Сбросить по умолчанию", "uk": "Скинути на стандарт"},
    "default_label": {"en": "Default", "ru": "По умолчанию", "uk": "За замовчуванням"},
    "job_started": {"en": "Job started...", "ru": "Задача запущена\u2026", "uk": "Завдання запущено\u2026"},
    "select_download": {"en": "Select what to download", "ru": "Выбор того, что скачать", "uk": "Вибір того, що завантажити"},
    "db_hint": {
        "en": "Text, reactions and metadata are already in the DB. Check media types \u2014 ETA will recalculate. Network speed:",
        "ru": "Текст, реакции и метаданные уже в БД. Отмечай типы медиа \u2014 ETA пересчитается под выбор. Скорость сети:",
        "uk": "Текст, реакції та метадані вже в БД. Обирай типи медіа \u2014 ETA перерахується під вибір. Швидкість мережі:",
    },
    "th_type": {"en": "Type", "ru": "Тип", "uk": "Тип"},
    "th_total": {"en": "Total", "ru": "Всего", "uk": "Всього"},
    "th_downloaded": {"en": "Downloaded", "ru": "Скачано", "uk": "Завантажено"},
    "th_remaining": {"en": "Remaining", "ru": "Осталось", "uk": "Залишилось"},
    "th_size_pending": {"en": "Size (not downloaded)", "ru": "Размер (не скачано)", "uk": "Розмір (не завантажено)"},
    "already_downloaded": {"en": "already downloaded", "ru": "уже скачано", "uk": "вже завантажено"},
    "already_in_db": {"en": "already in DB", "ru": "уже в БД", "uk": "вже в БД"},
    "selected": {"en": "Selected", "ru": "Выбрано", "uk": "Обрано"},
    "files": {"en": "files", "ru": "файлов", "uk": "файлів"},
    "est_time": {"en": "estimated time", "ru": "расчётное время", "uk": "орієнтовний час"},
    "download_selected": {"en": "Download selected", "ru": "Скачать выбранное", "uk": "Завантажити обране"},

    # JS strings
    "js_drives": {"en": "Drives", "ru": "Диски", "uk": "Диски"},
    "js_no_subfolders": {"en": "No subfolders", "ru": "Нет подпапок", "uk": "Немає підпапок"},
    "js_new_folder_prompt": {"en": "New folder name:", "ru": "Имя новой папки:", "uk": "Ім'я нової папки:"},
    "js_error": {"en": "Error", "ru": "Ошибка", "uk": "Помилка"},
    "js_job_not_found": {"en": "Job not found (server restart?)", "ru": "Задача не найдена (перезапуск сервера?)", "uk": "Завдання не знайдено (перезапуск сервера?)"},
    "js_done_files": {"en": "Done \u2014 %(n)s files", "ru": "Готово \u2014 %(n)s файлов", "uk": "Готово \u2014 %(n)s файлів"},
    "js_done_nothing": {"en": "Done \u2014 nothing to download", "ru": "Готово \u2014 нечего скачивать", "uk": "Готово \u2014 нічого завантажувати"},
    "js_s": {"en": "s", "ru": "с", "uk": "с"},
    "js_m": {"en": "m", "ru": "м", "uk": "хв"},
    "js_h": {"en": "h", "ru": "ч", "uk": "год"},

    # --- transcription ---
    "transcription_title": {"en": "Transcription", "ru": "Транскрипция", "uk": "Транскрипція"},
    "transcribe_hint": {
        "en": "%(n)s files awaiting transcription (speech-to-text via Whisper). Select types and press start.",
        "ru": "%(n)s файлов ждут транскрипции (речь в текст через Whisper). Выбери типы и нажми старт.",
        "uk": "%(n)s файлів чекають транскрипції (мовлення в текст через Whisper). Обери типи і натисни старт.",
    },
    "transcribe_done": {"en": "All transcribed", "ru": "Все транскрибированы", "uk": "Усі транскрибовано"},
    "tr_transcribed": {"en": "Transcribed", "ru": "Готово", "uk": "Готово"},
    "tr_pending": {"en": "Pending", "ru": "Ожидает", "uk": "Очікує"},
    "tr_start": {"en": "Start transcription", "ru": "Начать транскрипцию", "uk": "Почати транскрипцію"},
    "js_done_transcribed": {
        "en": "Done \u2014 %(n)s transcribed",
        "ru": "Готово \u2014 %(n)s транскрибировано",
        "uk": "Готово \u2014 %(n)s транскрибовано",
    },

    # --- media type labels ---
    "type_text": {"en": "Text", "ru": "Текст", "uk": "Текст"},
    "type_voice": {"en": "Voice", "ru": "Голосовые", "uk": "Голосові"},
    "type_audio": {"en": "Audio", "ru": "Аудио", "uk": "Аудіо"},
    "type_video_note": {"en": "Video notes", "ru": "Кружочки", "uk": "Кружечки"},
    "type_photo": {"en": "Photo", "ru": "Фото", "uk": "Фото"},
    "type_video": {"en": "Video", "ru": "Видео", "uk": "Відео"},
    "type_document": {"en": "Files", "ru": "Файлы", "uk": "Файли"},
    "type_other": {"en": "Other", "ru": "Другое", "uk": "Інше"},

    # single-form type labels (for message cards)
    "type_s_voice": {"en": "Voice", "ru": "Голосовое", "uk": "Голосове"},
    "type_s_audio": {"en": "Audio", "ru": "Аудио", "uk": "Аудіо"},
    "type_s_video_note": {"en": "Video note", "ru": "Кружочек", "uk": "Кружечок"},
    "type_s_photo": {"en": "Photo", "ru": "Фото", "uk": "Фото"},
    "type_s_video": {"en": "Video", "ru": "Видео", "uk": "Відео"},
    "type_s_document": {"en": "File", "ru": "Файл", "uk": "Файл"},

    # --- messages page ---
    "messages_title": {"en": "Messages", "ru": "Сообщения", "uk": "Повідомлення"},
    "messages_count": {"en": "messages", "ru": "сообщений", "uk": "повідомлень"},
    "search_label": {"en": "search", "ru": "поиск", "uk": "пошук"},
    "search_placeholder": {"en": "Search text and transcriptions...", "ru": "Поиск по тексту и транскрипциям...", "uk": "Пошук по тексту і транскрипціям..."},
    "all_types": {"en": "All types", "ru": "Все типы", "uk": "Усі типи"},
    "find": {"en": "Find", "ru": "Найти", "uk": "Знайти"},
    "reset": {"en": "Reset", "ru": "Сбросить", "uk": "Скинути"},
    "views": {"en": "views", "ru": "views", "uk": "views"},
    "nothing_found": {"en": "Nothing found.", "ru": "Ничего не найдено.", "uk": "Нічого не знайдено."},
    "page_of": {"en": "Page %(page)s of %(total)s", "ru": "Страница %(page)s из %(total)s", "uk": "Сторінка %(page)s з %(total)s"},
    "prev": {"en": "Back", "ru": "Назад", "uk": "Назад"},
    "next": {"en": "Forward", "ru": "Вперёд", "uk": "Вперед"},

    # --- errors / auth ---
    "auth_needed_title": {
        "en": "Telegram not connected",
        "ru": "Telegram не подключён",
        "uk": "Telegram не підключено",
    },
    "auth_needed_hint": {
        "en": "Run <code>tgp auth</code> in the terminal to connect your Telegram account, then refresh this page.",
        "ru": "Выполни <code>tgp auth</code> в терминале, чтобы подключить Telegram-аккаунт, затем обнови страницу.",
        "uk": "Виконай <code>tgp auth</code> в терміналі, щоб підключити Telegram-акаунт, потім онови сторінку.",
    },
    "err_auth_needed": {
        "en": "Run 'tgp auth' in the terminal first",
        "ru": "Сначала выполни: tgp auth",
        "uk": "Спочатку виконай: tgp auth",
    },
    "err_session_expired": {
        "en": "Session expired. Run 'tgp auth' again",
        "ru": "Сессия истекла. Выполни: tgp auth",
        "uk": "Сесія закінчилась. Виконай: tgp auth",
    },
    "err_channel_not_found": {
        "en": "Channel not found",
        "ru": "Канал не найден",
        "uk": "Канал не знайдено",
    },
    "err_channel_not_found_tg": {
        "en": "Channel '%(name)s' not found on Telegram",
        "ru": "Канал '%(name)s' не найден в Telegram",
        "uk": "Канал '%(name)s' не знайдено в Telegram",
    },

    # --- search page ---
    "search_title": {"en": "Search", "ru": "Поиск", "uk": "Пошук"},
    "search_all_placeholder": {"en": "Search across all channels...", "ru": "Поиск по всем каналам...", "uk": "Пошук по всіх каналах..."},
    "found": {"en": "Found", "ru": "Найдено", "uk": "Знайдено"},
    "nothing_found_query": {
        "en": "Nothing found for \"%(q)s\".",
        "ru": "Ничего не найдено по запросу \"%(q)s\".",
        "uk": "Нічого не знайдено за запитом \"%(q)s\".",
    },
}


def t(key: str, lang: str = DEFAULT_LANG, **kwargs) -> str:
    """Get translated string. Use %(name)s placeholders for interpolation."""
    entry = _STRINGS.get(key)
    if not entry:
        return key
    text = entry.get(lang, entry.get(DEFAULT_LANG, key))
    if kwargs:
        text = text % kwargs
    return text


def get_type_label(key: str, lang: str = DEFAULT_LANG) -> str:
    """Get human-readable media type label (plural form for tables)."""
    return t(f"type_{key}", lang)


def get_type_label_single(key: str, lang: str = DEFAULT_LANG) -> str:
    """Get human-readable media type label (single form for message badges)."""
    return t(f"type_s_{key}", lang)
