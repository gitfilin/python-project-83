"""
Page Analyzer - приложение для анализа веб-страниц.
"""

# Импорт стандартных библиотек
import os  # Работа с переменными окружения
from typing import Any  # Типизация переменных
from datetime import datetime  # Работа с датой и временем

# Импорт сторонних библиотек
import psycopg2  # Подключение к PostgreSQL
from psycopg2.extras import DictCursor  # Представление результатов запроса в виде словаря
from flask import Flask, render_template, request, redirect, url_for, flash  # Flask-модули
import validators  # Валидация URL-адресов
from urllib.parse import urlparse  # Разбор URL на компоненты
import requests  # Отправка HTTP-запросов
from bs4 import BeautifulSoup  # Парсинг HTML-контента
from dotenv import load_dotenv  # Загрузка переменных окружения из .env

# Загружаем переменные окружения перед их использованием
load_dotenv()

# Импорт локальных модулей (из проекта)
from page_analyzer.url_repository import UrlRepository

# Инициализация Flask-приложения
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')  # Устанавливаем секретный ключ
app.debug = True  # Включаем режим отладки

# Настройка базы данных
DATABASE_URL = os.getenv('DATABASE_URL')
repo = UrlRepository(DATABASE_URL)

# Функция для получения соединения с базой данных
def get_connection():
    """Создаёт соединение с базой данных."""
    try:
        return psycopg2.connect(DATABASE_URL)
    except Exception as e:
        print(f"Ошибка подключения к БД: {e}")
        raise


@app.route('/')
def index() -> str:
    """Отображает главную страницу."""
    return render_template('index.html')


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

    with get_connection() as conn:
        with conn.cursor() as cur:
            # Проверка на существование URL
            cur.execute('SELECT * FROM urls WHERE name = %s',
                        (normalized_url,))
            if cur.fetchone():
                flash('Страница уже существует', 'danger')
                return redirect(url_for('index'))

            created_at = datetime.now()
            cur.execute(
                'INSERT INTO urls (name, created_at) VALUES (%s, %s) RETURNING id',
                (normalized_url, created_at)
            )
            url_id = cur.fetchone()[0]
            conn.commit()

    flash('Страница успешно добавлена', 'success')
    return redirect(url_for('show_url', id=url_id))


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
def urls_list() -> str:
    """Отображает список всех добавленных URL."""
    with get_connection() as conn:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute('''
                SELECT 
                    urls.id,
                    urls.name,
                    TO_CHAR(urls.created_at, 'YYYY-MM-DD') as created_at,
                    COALESCE(TO_CHAR(last_check.created_at, 'YYYY-MM-DD'), '') as last_check_at,
                    COALESCE(last_check.status_code::text, '') as last_check_status
                FROM urls
                LEFT JOIN (
                    SELECT url_id, 
                           status_code,
                           created_at,
                           ROW_NUMBER() OVER (PARTITION BY url_id ORDER BY created_at DESC) as rn
                    FROM url_checks
                ) as last_check ON urls.id = last_check.url_id AND last_check.rn = 1
                ORDER BY urls.created_at DESC
            ''')
            urls = cur.fetchall()
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
