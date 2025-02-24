"""
Page Analyzer - приложение для анализа веб-страниц.
"""

# Стандартные библиотеки
import os
from typing import Optional, Dict, List, Any
from datetime import datetime

# Сторонние зависимости
import psycopg2
from psycopg2.extras import DictCursor
from flask import Flask, render_template, request, redirect, url_for, flash
from dotenv import load_dotenv
import validators
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup

# Загружаем переменные окружения из .env файла
load_dotenv()

# Инициализируем приложение Flask
app = Flask(__name__)
# Секретный ключ
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.debug = True  # Включаем режим отладки

# URL для подключения к базе данных из переменных окружения
DATABASE_URL = os.getenv('DATABASE_URL')


def get_connection():
    # пытаемся подключиться к базе данных
    try:
        return psycopg2.connect(DATABASE_URL)
    except Exception as e:
        # в случае сбоя подключения будет выведено сообщение
        print(f"Ошибка подключения к БД: {e}")
        raise


@app.route('/')
def index() -> str:
    """Отображает главную страницу.

    """
    return render_template('index.html')


@app.post('/urls')
def add_url() -> Any:
    """Добавляет новый URL в базу данных.

    Проверяет валидность URL и сохраняет в базу данных.

    """
    # Получаем URL из формы
    url = request.form.get('url')

    # Проверяем что URL не пустой
    if not url:
        flash('URL обязателен', 'danger')
        return redirect(url_for('index'))

    # Проверяем валидность URL и его длину
    if not validators.url(url) or len(url) > 255:
        flash('Некорректный URL', 'danger')
        return redirect(url_for('index'))

    # Нормализуем URL
    parsed_url = urlparse(url)
    normalized_url = f"{parsed_url.scheme}://{parsed_url.netloc}"

    # Получаем текущее время для created_at
    created_at = datetime.now()

    # Сохраняем URL в БД
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                'INSERT INTO urls (name, created_at) VALUES (%s, %s) RETURNING id',
                (normalized_url, created_at)
            )
            url_id = cur.fetchone()[0]  # Получаем ID добавленной записи
            conn.commit()  # Подтверждаем транзакцию

    # Сообщаем об успехе и перенаправляем на страницу URL
    flash('Страница успешно добавлена', 'success')
    return redirect(url_for('show_url', id=url_id))


@app.route('/urls/<int:id>')
def show_url(id: int) -> str:
    """Отображает информацию о конкретном URL."""
    with get_connection() as conn:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            # Получаем информацию об URL
            cur.execute('''
                SELECT id, name, TO_CHAR(created_at, 'YYYY-MM-DD') as created_at
                FROM urls WHERE id = %s
            ''', (id,))
            url = cur.fetchone()

            if url is None:
                flash('URL не найден', 'danger')
                return redirect(url_for('urls_list'))

            # Получаем все проверки для URL
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

            url = url_record[1]  # Получаем имя URL из записи

            # Выполняем запрос к сайту
            try:
                response = requests.get(url)
                response.raise_for_status()  # Проверяем статус ответа
                status_code = response.status_code  # Получаем код ответа

                # Парсим HTML с помощью BeautifulSoup
                soup = BeautifulSoup(response.text, 'html.parser')

                # Извлекаем данные
                h1 = soup.find('h1').get_text() if soup.find('h1') else ''
                title = soup.title.string if soup.title else ''
                description = soup.find('meta', attrs={'name': 'description'})
                description_content = description['content'] if description else ''

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
    app.run(debug=True)
