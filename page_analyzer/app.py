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
# Настраиваем тип сессии для корректной работы flash-сообщений
app.config['SESSION_TYPE'] = 'filesystem'

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

# READ -  Отображает главную страницу


@app.route('/')
def index():
    """Отображает главную страницу."""
    raw_url = session.pop('raw_url', '')  # Извлекаем и очищаем сохранённый URL
    # Логируем текущие flash-сообщения
    logging.info(f"Current flash messages: {session.get('_flashes', [])}")
    # Загружаем HTML-шаблон
    return render_template('index.html', raw_url=raw_url)

# CREATE - создание нового URL


@app.post('/urls')
def add_url():
    """Добавляет новый URL в базу данных."""
    raw_url = request.form.get('url', '').strip()  # Получаем URL из формы
    session['raw_url'] = raw_url  # Сохраняем URL в сессии

    if not raw_url:  # Проверяем на пустой URL
        flash('URL обязателен', 'danger')  # Показываем ошибку
        # Логируем добавление сообщения
        logging.info("Flash message added: URL обязателен")
        response = redirect(url_for('index'))  # Создаем ответ
        response.status_code = 422  # Устанавливаем код статуса
        return response  # Возвращаем ответ

    if not validators.url(raw_url) or len(raw_url) > 255:  # Проверяем валидность URL
        flash('Некорректный URL', 'danger')  # Показываем ошибку
        # Логируем добавление сообщения
        logging.info("Flash message added: Некорректный URL")
        response = redirect(url_for('index'))  # Создаем ответ
        response.status_code = 422  # Устанавливаем код статуса
        return response  # Возвращаем ответ

    parsed = urlparse(raw_url)  # Разбираем URL на компоненты
    normalized_url = f"{parsed.scheme}://{parsed.netloc}"  # Нормализуем URL

    existing_url = repo.find_url(normalized_url)  # Ищем URL в БД

    if existing_url:  # Если URL существует
        flash('Страница уже существует', 'success')  # Показываем сообщение
        session.pop('raw_url', None)  # Очищаем сессию
        # Перенаправляем
        return redirect(url_for('show_url', id=existing_url['id']))

    new_url = {'name': normalized_url}  # Создаем данные для сохранения
    new_url_id = repo.save(new_url)  # Сохраняем URL
    flash('Страница успешно добавлена', 'success')  # Показываем успех
    session.pop('raw_url', None)  # Очищаем сессию
    return redirect(url_for('show_url', id=new_url_id))  # Перенаправляем

# READ - получение списка URL


@app.route('/urls', methods=['GET'])
def urls_show() -> str:
    """Отображает список всех добавленных URL."""
    urls = repo.get_content()
    return render_template('urls.html', urls=urls)


@app.route('/urls/<int:id>')
def show_url(id):
    """Отображает информацию о конкретном URL."""
    url, checks = repo.get_url_by_id(id)

    if url is None:
        flash('URL не найден', 'danger')
        return redirect(url_for('urls_show'))

    return render_template('url.html', url=url, checks=checks)


# Создание проверки для URL


@app.post('/urls/<int:id>/checks')
def check_url(id):
    """Создает новую проверку для указанного URL."""
    url_data = repo.get_url_by_id(id)
    if not url_data or not url_data[0]:
        flash('URL не найден', 'danger')
        return redirect(url_for('urls_show'))

    url = url_data[0]

    try:
        response = requests.get(url['name'], timeout=5)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')

        check_data = {
            'status_code': response.status_code,
            'h1': soup.h1.text.strip() if soup.h1 else '',
            'title': soup.title.text.strip() if soup.title else '',
            'description': soup.find('meta', {'name': 'description'})['content'].strip()
            if soup.find('meta', {'name': 'description'}) else ''
        }

        repo.save_check(id, check_data)
        flash('Страница успешно проверена', 'success')

    except requests.RequestException:
        flash('Произошла ошибка при проверке', 'danger')
        check_data = {
            'status_code': 500,
            'h1': '',
            'title': '',
            'description': ''
        }
        repo.save_check(id, check_data)

    return redirect(url_for('show_url', id=id))


if __name__ == '__main__':
    app.run(debug=False)
