[![Maintainability](https://qlty.sh/gh/gitfilin/projects/python-project-83/maintainability.svg)](https://qlty.sh/gh/gitfilin/projects/python-project-83)
[![Code Coverage](https://qlty.sh/gh/gitfilin/projects/python-project-83/coverage.svg)](https://qlty.sh/gh/gitfilin/projects/python-project-83)
### Hexlet tests and linter status:
[![Actions Status](https://github.com/gitfilin/python-project-83/actions/workflows/hexlet-check.yml/badge.svg)](https://github.com/gitfilin/python-project-83/actions)
# Page Analyzer

[![Deployed on Render](https://img.shields.io/badge/Render-Live_Project-000000?style=for-the-badge&logo=render)](https://python-project-83-1-b6lx.onrender.com)

> 🚀 Рабочая версия: [python-project-83-1-b6lx.onrender.com](https://python-project-83-1-b6lx.onrender.com)



## Описание проекта

Page Analyzer - это веб-приложение, которое позволяет пользователям добавлять URL-адреса и проверять их доступность. Приложение выполняет SEO-анализ, извлекая информацию о заголовках, мета-тегах и других элементах страницы. Оно использует Flask для создания веб-интерфейса и PostgreSQL для хранения данных.

### Основные функции:

- Добавление URL-адресов.
- Проверка доступности сайтов с получением кода ответа.
- Извлечение и хранение SEO-данных (теги `<h1>`, `<title>`, и мета-тег `description`).
- Отображение списка добавленных URL-адресов и их последней проверки.

## Установка

### Предварительные требования

- Python 3.10 или выше
- PostgreSQL
- pip (Python package installer)

### Шаги для запуска проекта

1. **Клонируйте репозиторий:**

   ```bash
   git clone https://github.com/gitfilin/python-project-83.git
   cd python-project-83
   ```

2. **Установите зависимости для локальной разработки (через `uv` и `pyproject.toml`):**

   ```bash
   make install
   # или
   uv sync
   ```

3. **Настройте базу данных:**

   Создайте базу данных PostgreSQL и настройте переменные окружения в файле `.env` в корне проекта:

   ```env
   DATABASE_URL=postgresql://username:password@localhost:5432/page_analyzer
   SECRET_KEY=your_secret_key
   ```

4. **Создайте таблицы в базе данных:**

   ```bash
   export $(cat .env | xargs)
   psql -d "$DATABASE_URL" -f database.sql
   ```

5. **Запустите приложение для локальной разработки:**

   ```bash
   make dev
   # или
   uv run flask --debug --app page_analyzer:app run
   ```

6. **Откройте браузер и перейдите по адресу:**

   ```text
   http://localhost:5000
   ```

## Развертывание на Render.com

1. **Создайте новый Web Service на Render.com и подключите этот репозиторий.**
2. **В разделе Build Command укажите:**

   ```text
   ./build.sh
   ```

3. **В разделе Start Command укажите:**

   ```text
   make render-start
   ```

4. **Настройте переменные окружения в настройках сервиса:**

   - `DATABASE_URL` — строка подключения к базе данных PostgreSQL на Render
   - `SECRET_KEY` — произвольная секретная строка для Flask‑сессий

5. **Сохраните настройки и дождитесь деплоя приложения.**

## Использование

- Добавьте URL-адрес в форму на главной странице.
- Нажмите кнопку для проверки доступности сайта.
- Просмотрите результаты проверки и SEO-данные.