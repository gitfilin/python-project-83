### Hexlet tests and linter status:
[![Actions Status](https://github.com/gitfilin/python-project-83/actions/workflows/hexlet-check.yml/badge.svg)](https://github.com/gitfilin/python-project-83/actions)

[Посмотреть приложение](https://python-project-83-wiha.onrender.com)


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
   git clone https://github.com/yourusername/page_analyzer.git
   cd page_analyzer
   ```

2. **Создайте и активируйте виртуальное окружение:**

   ```bash
   python -m venv venv
   source venv/bin/activate  # Для Linux/Mac
   venv\Scripts\activate     # Для Windows
   ```

3. **Установите зависимости для локальной разработки:**

   ```bash
   pip install -r requirements.txt
   ```

4. **Настройте базу данных:**

   - Создайте базу данных PostgreSQL и настройте переменные окружения в файле `.env`:

     ```
     DATABASE_URL=postgresql://username:password@localhost:5432/page_analyzer
     SECRET_KEY=your_secret_key
     ```

5. **Запустите миграции базы данных:**

   Убедитесь, что в вашем проекте есть файл миграции, и выполните его, если необходимо.

6. **Запустите приложение для локальной разработки:**

   ```bash
   uv run gunicorn -w 5 -b 0.0.0.0:8000 app:app
   ```

7. **Откройте браузер и перейдите по адресу:**

   ```
   http://localhost:8000
   ```

## Развертывание на Render.com

1. **Создайте новый проект на Render.com.**
2. **Подключите ваш репозиторий.**
3. **Убедитесь, что Render использует файл `requirements.txt` для установки зависимостей.**
4. **Настройте переменные окружения в настройках вашего приложения на Render.com.**
5. **Запустите приложение.**

## Использование

- Добавьте URL-адрес в форму на главной странице.
- Нажмите кнопку для проверки доступности сайта.
- Просмотрите результаты проверки и SEO-данные.
