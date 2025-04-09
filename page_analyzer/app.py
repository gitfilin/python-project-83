# Стандартные библиотеки
import os  # Работа с переменными окружения и файловой системой
import logging  # Логирование событий и ошибок приложения
from typing import Any  # Аннотации типов для статического анализа кода

# Внешние зависимости
import psycopg2  # Адаптер для работы с PostgreSQL
# Веб-фреймворк Flask и его компоненты
from flask import Flask, render_template, request, redirect, url_for, flash, session
import validators  # Валидация различных типов данных, включая URL
from urllib.parse import urlparse  # Парсинг URL на составные части
import requests  # Отправка HTTP-запросов к веб-страницам
from bs4 import BeautifulSoup  # Парсинг HTML-контента страниц
from dotenv import load_dotenv  # Загрузка переменных окружения из .env файла

# Локальные модули
# Репозиторий для работы с URL в БД
from page_analyzer.url_repository import UrlRepository

# Загружаем переменные окружения из .env файла
load_dotenv()


def configure_logging():
    """Настройка базовой конфигурации логирования для приложения.

    Устанавливает:
    - Уровень логирования (по умолчанию INFO)
    - Формат сообщений: время-уровень-сообщение
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )


# Инициализация Flask-приложения
app = Flask(__name__)  # Создание основного объекта Flask-приложения
app.config['SECRET_KEY'] = os.getenv(
    'SECRET_KEY')  # Секретный ключ для сессий
app.debug = os.getenv("FLASK_DEBUG", "False").lower(
) == "true"  # Режим отладки из переменных окружения
app.config['SESSION_TYPE'] = 'filesystem'  # Хранение сессий в файловой системе

# Настройка подключения к базе данных
# Получаем строку подключения из переменных окружения
DATABASE_URL = os.getenv('DATABASE_URL')


def create_database_connection():
    """Создает и возвращает соединение с PostgreSQL базой данных.

    Returns:
        psycopg2.connection: Объект соединения с БД

    Raises:
        RuntimeError: Если подключение не удалось
    """
    try:
        return psycopg2.connect(DATABASE_URL)
    except psycopg2.Error as e:
        logging.critical(f"Не удалось подключиться к базе данных: {e}")
        raise RuntimeError("Database connection failed")


# Инициализация соединения и репозитория
conn = create_database_connection()
repo = UrlRepository(conn)  # Создаем экземпляр репозитория для работы с URL


@app.route('/')
def index():
    """Обрабатывает GET-запросы к корневому URL.

    Returns:
        str: HTML-страница из шаблона index.html
    """
    return render_template('index.html')


@app.route('/urls', methods=['POST'])
def add_url():
    """Обрабатывает добавление нового URL.

    Steps:
    1. Валидирует введенный URL
    2. Нормализует URL (убирает лишние части)
    3. Проверяет существование URL в БД
    4. Сохраняет новый URL или перенаправляет на существующий

    Returns:
        Response: Редирект на страницу URL или отображение формы с ошибками
    """
    raw_url = request.form.get('url', '').strip(
    )  # Получаем URL из формы, удаляем пробелы

    # Валидация URL
    if not raw_url:
        flash('URL обязателен', 'danger')
        return render_template('index.html', raw_url=raw_url), 422

    if not validators.url(raw_url) or len(raw_url) > 255:
        flash('Некорректный URL', 'danger')
        return render_template('index.html', raw_url=raw_url), 422

    try:
        parsed = urlparse(raw_url)  # Разбираем URL на компоненты
        # Нормализуем URL
        normalized_url = f"{parsed.scheme}://{parsed.netloc}"
    except Exception as e:
        logging.error(f"Ошибка парсинга URL {raw_url}: {e}")
        flash('Некорректный URL', 'danger')
        return render_template('index.html', raw_url=raw_url), 422

    # Проверка существования URL в БД
    existing_url = repo.find_url(normalized_url)
    if existing_url:
        flash('Страница уже существует', 'info')
        return redirect(url_for('show_url', id=existing_url['id']))

    # Сохранение нового URL
    new_url_id = repo.save({'name': normalized_url})
    flash('Страница успешно добавлена', 'success')
    return redirect(url_for('show_url', id=new_url_id))


@app.route('/urls')
def urls_show() -> str:
    """Отображает список всех URL с их последними проверками.

    Returns:
        str: HTML-страница со списком URL из шаблона urls.html
    """
    urls = repo.get_content()  # Получаем все URL из БД
    latest_checks = repo.get_latest_checks()  # Получаем последние проверки

    # Собираем данные для отображения
    urls_with_checks = []
    for url in urls:
        check = latest_checks.get(url['id'])
        urls_with_checks.append((url, check))

    return render_template('urls.html', urls_with_checks=urls_with_checks)


@app.route('/url/<int:id>')
def show_url(id: int):
    """Отображает детальную информацию о конкретном URL.

    Args:
        id (int): Идентификатор URL в базе данных

    Returns:
        Response: Страница с информацией о URL или редирект при ошибке
    """
    url, checks = repo.get_url_by_id(id)

    if url is None:
        flash('URL не найден', 'danger')
        return redirect(url_for('urls_show'))

    return render_template('url.html', url=url, checks=checks)


@app.post('/urls/<int:id>/checks')
def check_url(id: int):
    """Выполняет проверку указанного URL и сохраняет результаты.

    Args:
        id (int): Идентификатор URL для проверки

    Returns:
        Response: Редирект обратно на страницу URL
    """
    url_data = repo.get_url_by_id(id)
    if not url_data or not url_data[0]:
        flash('URL не найден', 'danger')
        return redirect(url_for('urls_show'))

    url = url_data[0]

    try:
        # Выполняем HTTP-запрос
        response = requests.get(url['name'], timeout=5)
        response.raise_for_status()  # Проверяем на ошибки HTTP

        # Парсим HTML-контент
        soup = BeautifulSoup(response.text, 'html.parser')
        check_data = {
            'status_code': response.status_code,
            'h1': soup.h1.text.strip() if soup.h1 else '',
            'title': soup.title.text.strip() if soup.title else '',
            'description': soup.find('meta', {'name': 'description'})['content'].strip()
            if soup.find('meta', {'name': 'description'}) else ''
        }

        # Сохраняем результаты проверки
        repo.save_check(id, check_data)
        flash('Страница успешно проверена', 'success')
    except requests.RequestException as e:
        logging.error(f"Ошибка HTTP при проверке URL {url['name']}: {e}")
        flash('Не удалось получить доступ к странице', 'danger')
    except Exception as e:
        logging.error(f"Ошибка при проверке URL: {e}")
        flash('Произошла ошибка при проверке', 'danger')

    return redirect(url_for('show_url', id=id))


if __name__ == '__main__':
    """Точка входа при запуске приложения напрямую."""
    configure_logging()
    app.run(debug=app.debug)  # Запуск Flask-приложения
