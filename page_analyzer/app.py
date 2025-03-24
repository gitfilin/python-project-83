"""
Page Analyzer - приложение для анализа веб-страниц.
"""

# Стандартные библиотеки
import os  # Работа с переменными окружения
import logging  # Логирование событий приложения
from datetime import datetime  # Работа с датой и временем
from typing import Any  # Использование аннотаций типов для лучшей читаемости кода


# Основной веб-фреймворк
from flask import Flask, render_template, request, redirect, url_for, flash, Response, session
import validators  # Валидация URL-адресов
# Разбор URL на компоненты (схема, домен, путь и т. д.)
from urllib.parse import urlparse
import requests  # Отправка HTTP-запросов (GET, POST и др.)
from bs4 import BeautifulSoup  # Парсинг HTML-контента
from dotenv import load_dotenv  # Загрузка переменных окружения из .env-файла

# Локальные модули (из проекта)
# Класс для работы с базой данных
from page_analyzer.url_repository import UrlRepository

# Загружаем переменные окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    # Уровень логирования (INFO, DEBUG, WARNING, ERROR, CRITICAL)
    level=logging.INFO,
    # Формат сообщений в логах
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# Инициализация Flask-приложения
app = Flask(__name__)  # Создание экземпляра Flask
# Устанавливаем секретный ключ для защиты сессий
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-default-secret-key')
# Включаем режим отладки, если указано в .env
app.debug = os.getenv("FLASK_DEBUG", "False").lower() == "true"

# Настройка базы данных
# Получаем URL базы данных из переменных окружения
DATABASE_URL = os.getenv('DATABASE_URL')
# Создаем экземпляр репозитория для работы с БД
repo = UrlRepository(DATABASE_URL)

# Проверяем соединение с БД
try:
    with repo.get_connection() as conn:  # Устанавливаем соединение с БД
        with conn.cursor() as cur:  # Открываем курсор для выполнения SQL-запросов
            cur.execute("SELECT 1")  # Проверяем работоспособность БД
    logging.info("✅ Соединение с базой данных установлено")
except Exception as e:
    logging.critical(f"❌ Ошибка подключения к базе данных: {e}")
    exit(1)  # Завершаем приложение при критической ошибке подключения к БД


@app.route('/')
def index() -> Response:
    """Отображает главную страницу."""
    return render_template('index.html')  # Загружаем HTML-шаблон


@app.post('/urls')
def add_url() -> Any:
    """Добавляет новый URL в базу данных."""
    url = request.form.get('url')

    if not url:
        flash('URL обязателен', 'danger')
        return redirect(url_for('index'))

    if not validators.url(url) or len(url) > 255:
        flash('Некорректный URL', 'danger')
        return redirect(url_for('index'))

    parsed_url = urlparse(url)
    normalized_url = f"{parsed_url.scheme}://{parsed_url.netloc}"

    # Проверка на существование URL
    url = repo.find(normalized_url)

    if not url:
        created_at = datetime.now()

        flash('Страница успешно добавлена', 'success')
        return redirect(url_for('show_url', id=url))

    flash('Страница уже существует', 'danger')
    return redirect(url_for('show_url', id))


@app.route('/urls/<int:id>')
def show_url(id: int) -> str:
    """Отображает информацию о конкретном URL."""
    with get_connection() as conn:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute('''
                SELECT id, name, TO_CHAR(created_at, 'YYYY-MM-DD') as created_at
                FROM urls WHERE id = %s
            ''', (id,))
            url = cur.fetchone()

            if url is None:
                flash('URL не найден', 'danger')
                return redirect(url_for('urls_list'))

            cur.execute('''
                SELECT id, status_code, h1, title, description,
                       TO_CHAR(created_at, 'YYYY-MM-DD') as created_at
                FROM url_checks
                WHERE url_id = %s
                ORDER BY id DESC
            ''', (id,))
            checks = cur.fetchall()

    return render_template('url.html', url=url, checks=checks)


@app.route('/urls')
def urls_show() -> str:
    """Отображает список всех добавленных URL."""
    session.pop('_flashes', None)  # очищаем flash-сообщения
    urls = repo.get_content()
    return render_template('urls.html', urls=urls)


@app.post('/urls/<int:id>/checks')
def check_url(id: int) -> Any:
    """Создает новую проверку для указанного URL."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            # Проверяем существование URL
            cur.execute('SELECT id, name FROM urls WHERE id = %s', (id,))
            url_record = cur.fetchone()
            if not url_record:
                flash('URL не найден', 'danger')
                return redirect(url_for('urls_list'))

            url = url_record[1]

            # Выполняем запрос к сайту
            try:
                response = requests.get(url)
                response.raise_for_status()
                status_code = response.status_code

                # Парсим HTML с помощью BeautifulSoup
                soup = BeautifulSoup(response.text, 'html.parser')
                h1 = soup.find('h1').get_text() if soup.find('h1') else ''
                title = soup.title.string if soup.title else ''
                description = soup.find('meta', attrs={'name': 'description'})
                description_content = description['content'] if description else ''

                # Проверяем, была ли уже проверка для этого URL
                cur.execute(
                    'SELECT * FROM url_checks WHERE url_id = %s AND created_at >= NOW() - INTERVAL \'1 DAY\'', (id,))
                if cur.fetchone():
                    # Если проверка уже была, перенаправляем на страницу с URL
                    flash(
                        'Проверка уже была выполнена для этого URL в течение последнего дня.', 'info')
                    return redirect(url_for('show_url', id=id))

                # Создаем новую проверку
                cur.execute(
                    'INSERT INTO url_checks (url_id, status_code, h1, title, description, created_at) VALUES (%s, %s, %s, %s, %s, %s)',
                    (id, status_code, h1, title, description_content, datetime.now())
                )
                conn.commit()
                flash('Страница успешно проверена', 'success')
            except requests.RequestException:
                flash('Произошла ошибка при проверке', 'danger')

    return redirect(url_for('show_url', id=id))


if __name__ == '__main__':
    app.run(debug=False)
