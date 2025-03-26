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

# READ -  Отображает главную страницу


@app.route('/')
def index():
    """Отображает главную страницу."""
    raw_url = session.pop('raw_url', '')  # Извлекаем и очищаем сохранённый URL
    # Загружаем HTML-шаблон
    return render_template('index.html', raw_url=raw_url)

# CREATE - создание нового URL


@app.post('/urls')
def add_url():
    """Добавляет новый URL в базу данных."""
    # Получаем URL из формы и удаляем пробелы в начале и конце
    raw_url = request.form.get('url', '').strip()
    # Сохраняем введенный URL в сессии для возврата при ошибке
    session['raw_url'] = raw_url

    # Проверяем, что URL не пустой
    if not raw_url:
        flash('URL обязателен', 'danger')
        return redirect(url_for('index'))

    # Проверяем корректность URL и его длину
    if not validators.url(raw_url) or len(raw_url) > 255:
        flash('Некорректный URL', 'danger')
        return redirect(url_for('index'))

    # Разбираем URL на компоненты
    parsed_url = urlparse(raw_url)
    # Формируем нормализованный URL (только схема и домен)
    normalized_url = f"{parsed_url.scheme}://{parsed_url.netloc}"

    # Ищем URL в базе данных
    url_data = repo.find_url(normalized_url)
    # Если URL уже существует, перенаправляем на его страницу
    if url_data:
        flash('Страница уже существует', 'success')
        session.pop('raw_url', None)
        return redirect(url_for('show_url', id=url_data['id']))

    try:
        # Создаем словарь с данными для сохранения
        new_url = {'name': normalized_url}
        # Сохраняем URL в базу данных
        new_url_id = repo.save(new_url)
        # Логируем успешное добавление URL
        logging.info(f"Добавлен новый URL: {normalized_url}")

        flash('Страница успешно добавлена', 'success')
        session.pop('raw_url', None)
        return redirect(url_for('show_url', id=new_url_id))
    except Exception as e:
        # Логируем ошибку при сохранении
        logging.error(f"Ошибка при сохранении URL {normalized_url}: {str(e)}")
        flash('Произошла ошибка при сохранении URL', 'danger')
        return redirect(url_for('index'))

# READ - получение списка URL


@app.route('/urls', methods=['GET'])
def urls_show() -> str:
    """Отображает список всех добавленных URL."""
    session.pop('_flashes', None)  # Очищаем flash-сообщения
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
    # Получаем данные URL из базы данных
    url, _ = repo.get_url_by_id(id)

    # Проверяем существование URL
    if url is None:
        flash('URL не найден', 'danger')
        return redirect(url_for('urls_show'))

    # Отправляем GET-запрос к сайту с таймаутом 5 секунд
    response = requests.get(url['name'], timeout=5)
    # Проверяем статус ответа
    response.raise_for_status()

    # Создаем объект BeautifulSoup для парсинга HTML
    soup = BeautifulSoup(response.text, 'html.parser')

    # Собираем данные для проверки
    check_data = {
        'status_code': response.status_code,
        # Получаем текст из тега h1, если он есть
        'h1': soup.h1.text.strip() if soup.h1 else '',
        # Получаем текст из тега title, если он есть
        'title': soup.title.text.strip() if soup.title else '',
        # Получаем содержимое мета-тега description, если он есть
        'description': soup.find('meta', {'name': 'description'})['content'].strip()
        if soup.find('meta', {'name': 'description'}) else ''
    }

    # Сохраняем результаты проверки в базу данных
    repo.save_check(id, check_data)
    # Логируем успешную проверку
    logging.info(
        f"Успешная проверка URL {url['name']}: код {response.status_code}")

    flash('Страница успешно проверена', 'success')

    # Перенаправляем на страницу URL
    return redirect(url_for('show_url', id=id))


if __name__ == '__main__':
    app.run(debug=False)
