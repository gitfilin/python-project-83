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

# Загружаем переменные окружения из .env файла
load_dotenv()

# Инициализируем приложение Flask
app = Flask(__name__)
# Секретный ключ
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.debug = True  # Включаем режим отладки

# URL для подключения к базе данных из переменных окружения
DATABASE_URL = os.getenv('DATABASE_URL')


def get_connection() -> psycopg2.extensions.connection:
    """Создает и возвращает соединение с базой данных.

    Returns:
        psycopg2.extensions.connection: Объект соединения с базой данных
    """
    return psycopg2.connect(DATABASE_URL)


@app.route('/')
def index() -> str:
    """Отображает главную страницу.

    Returns:
        str: HTML-страница с формой для добавления URL
    """
    return render_template('index.html')


@app.post('/urls')
def add_url() -> Any:
    """Добавляет новый URL в базу данных.

    Проверяет валидность URL, нормализует его и сохраняет в базу данных.

    Returns:
        Response: Перенаправление на страницу URL или главную страницу в случае ошибки
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

    # Нормализуем URL, оставляя только схему и домен
    parsed_url = urlparse(url)
    normalized_url = f"{parsed_url.scheme}://{parsed_url.netloc}"

    # Получаем текущее время для created_at
    created_at = datetime.now()

    # Сохраняем URL в базу данных
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
    """Отображает информацию о конкретном URL.

    Args:
        id (int): Идентификатор URL в базе данных

    Returns:
        str: HTML-страница с информацией о URL
    """
    # Получаем информацию об URL из базы данных
    with get_connection() as conn:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            # Форматируем дату в нужный формат прямо в SQL-запросе
            cur.execute('''
                SELECT 
                    id,
                    name,
                    TO_CHAR(created_at, 'YYYY-MM-DD') as created_at
                FROM urls 
                WHERE id = %s
            ''', (id,))
            url = cur.fetchone()
    return render_template('url.html', url=url)


@app.route('/urls')
def urls_list() -> str:
    """Отображает список всех добавленных URL.

    Returns:
        str: HTML-страница со списком URL
    """
    # Получаем все URL из базы данных
    with get_connection() as conn:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            # Получаем список URL, отсортированный по дате создания
            cur.execute('''
                SELECT 
                    id,
                    name,
                    TO_CHAR(created_at, 'YYYY-MM-DD') as created_at
                FROM urls 
                ORDER BY created_at DESC
            ''')
            urls = cur.fetchall()
    return render_template('urls.html', urls=urls)


if __name__ == '__main__':
    app.run(debug=True)
