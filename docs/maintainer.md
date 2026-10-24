# Руководство мейнтейнера: релиз и поддержка yt-dlp-reddit

Этот документ — пошаговая памятка о том, как тестировать, версионировать и выпускать релизы плагина **yt-dlp-reddit**.

---

## 1. Структура проекта

```text
yt-dlp-reddit/
├── .github/
│   └── workflows/
│       └── release.yml          # GitHub Action: сборка zip и публикация релиза по тегу v*
├── yt_dlp_plugins/
│   └── extractor/
│       ├── __init__.py
│       └── reddit.py            # Код плагина (_RedditPluginIE)
├── docs/
│   └── maintainer.md            # Этот файл
├── pyproject.toml               # Метаданные проекта и версия для pip
├── setup.cfg                    # Конфигурация setuptools
├── README.md                    # Основное описание проекта
├── LICENSE                      # The Unlicense
└── yt-dlp-reddit.zip            # Локальный архив (не коммитится в git)
```

---

## 2. Локальное тестирование перед релизом

Перед выпуском новой версии проверьте, что плагин корректно работает:

```bash
# 1. Перейдите в корень репозитория
cd /Users/sla/FlutterProjects/src/yt-dlp-reddit

# 2. Соберите чистый тестовый zip-архив (без кэша pycache)
rm -f yt-dlp-reddit.zip
zip -r yt-dlp-reddit.zip yt_dlp_plugins/ -x "*/__pycache__/*"

# 3. Скопируйте в локальную папку плагинов yt-dlp
mkdir -p ~/.yt-dlp/plugins
cp yt-dlp-reddit.zip ~/.yt-dlp/plugins/

# 4. Проверьте запуск на проблемной ссылке
yt-dlp -v --skip-download 'https://www.reddit.com/r/Pikabu/comments/1xa1dkp/%D0%BC%D1%8F%D1%83%D0%BA%D1%80%D0%B0%D1%84%D1%82/'
```

В выводе должно присутствовать:
- `[debug] Extractor Plugins: shreddit (RedditIE)`
- `[Reddit+shreddit] ...`
- Завершение без ошибок.

---

## 3. Процесс создания нового релиза (Release Workflow)

### Шаг 1. Повысить номер версии
Номер версии нужно обновить в двух файлах:
1. `pyproject.toml`:
   ```toml
   [project]
   name = "yt-dlp-reddit"
   version = "0.1.1"   # <--- меняем версию
   ```
2. `setup.cfg`:
   ```ini
   [metadata]
   name = yt-dlp-reddit
   version = 0.1.1     # <--- меняем версию
   ```

### Шаг 2. Закоммитить изменения
```bash
git add pyproject.toml setup.cfg
git commit -m "Bump version to 0.1.1"
git push origin main
```

### Шаг 3. Создать и запушить тег версии
> **Важно**: Имя тега обязательно должно начинаться с буквы `v` (например, `v0.1.1`), так как GitHub Action настроен на шаблон `v*`.

```bash
git tag v0.1.1
git push origin v0.1.1
```

### Шаг 4. Автоматическая магия GitHub Actions
После отправки тега GitHub автоматически запустит workflow `.github/workflows/release.yml`, который:
1. Упакует папку `yt_dlp_plugins/` в чистый архив `yt-dlp-reddit.zip`.
2. Создаст новый **GitHub Release** с именем тега `v0.1.1`.
3. Прикрепит файл `yt-dlp-reddit.zip` к релизу.

Пользователи смогут скачать `yt-dlp-reddit.zip` со страницы релизов и положить в `~/.yt-dlp/plugins/`.

---

## 4. Альтернатива: Создание релиза через веб-интерфейс GitHub

Если лень вводить команды в терминале:

1. Откройте репозиторий на GitHub: `https://github.com/<username>/yt-dlp-reddit`.
2. Справа нажмите **Releases** -> **Draft a new release**.
3. В поле **Choose a tag** введите новый тег (например, `v0.1.1`) и выберите `Create new tag: v0.1.1 on publish`.
4. Введите заголовок релиза (например, `Release v0.1.1`) и кратко опишите изменения.
5. Нажмите зеленую кнопку **Publish release**.
6. GitHub Action сам соберет zip и добавит его во вложения к этому релизу.

---

## 5. Опционально: Публикация в PyPI (для `pip install yt-dlp-reddit`)

Если вы решите выложить плагин в глобальный индекс PyPI, чтобы любой человек мог установить его командой `pip install yt-dlp-reddit`:

```bash
# Установить инструменты сборки
pip install --upgrade build twine

# Собрать sdist и wheel
python3 -m build

# Загрузить в PyPI (потребуется API token от pypi.org)
twine upload dist/*
```

---

## 6. Шпаргалка для быстрой вставки (TL;DR Cheatsheet)

Когда нужно быстро выкатить фикс:

```bash
cd /Users/sla/FlutterProjects/src/yt-dlp-reddit

# 1. Правим код или баг
# 2. Обновляем версию в pyproject.toml и setup.cfg
git add .
git commit -m "Fix: description of changes"
git push origin main

# 3. Пушим тег (замените 0.1.1 на актуальную версию)
git tag v0.1.1
git push origin v0.1.1

# Готово! GitHub Actions сам создаст релиз и прикрепит zip.
```

