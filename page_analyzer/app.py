# Стандартные библиотеки
import os  # Работа с переменными окружения и файловой системой
import logging  # Логирование событий и ошибок приложения
from urllib.parse import urlparse  # Парсинг URL на составные части

# Внешние зависимости
import psycopg2  # Адаптер для работы с PostgreSQL
# Веб-фреймворк Flask и его компоненты
from flask import Flask, render_template, request, redirect, url_for, flash, session
import validators  # Валидация различных типов данных, включая URL
import requests  # Отправка HTTP-запросов к веб-страницам
from bs4 import BeautifulSoup  # Парсинг HTML-контента страниц
from dotenv import load_dotenv  # Загрузка переменных окружения из .env файла

# Локальные модули
# Репозиторий для работы с URL в БД
from page_analyzer.url_repository import UrlRepository

# Загружаем переменные окружения из .env файла
load_dotenv()


# Инициализация Flask-приложения
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['SESSION_TYPE'] = 'filesystem'
app.debug = os.getenv("FLASK_DEBUG", "False").lower() == "true"  # Debug режим

# Настройка логирования
logging.basicConfig(
    level=logging.DEBUG if app.debug else logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/urls', methods=['POST'])
def add_url():
    raw_url = request.form.get('url')
    
    if not raw_url:
        flash('URL обязателен', 'danger')
        return render_template('index.html', raw_url=raw_url), 422

    if not validators.url(raw_url) or len(raw_url) > 255:
        flash('Некорректный URL', 'danger')
        return render_template('index.html', raw_url=raw_url), 422

    try:
        parsed = urlparse(raw_url)
        normalized_url = f"{parsed.scheme}://{parsed.netloc}"
    except Exception as e:
        logging.error(f"Ошибка парсинга URL {raw_url}: {e}")
        flash('Некорректный URL', 'danger')
        return render_template('index.html', raw_url=raw_url), 422

    try:
        parsed = urlparse(raw_url)
        normalized_url = f"{parsed.scheme}://{parsed.netloc}"
    except Exception as e:
        logging.error(f"Ошибка парсинга URL {raw_url}: {e}")
        flash('Некорректный URL', 'danger')
        return render_template('index.html', raw_url=raw_url), 422

    with psycopg2.connect(os.getenv('DATABASE_URL')) as conn:
        repo = UrlRepository(conn)
        existing_url = repo.find_url(normalized_url)
        if existing_url:
            flash('Страница уже существует', 'info')
            return redirect(url_for('urls_show', id=existing_url['id']))

        new_url_id = repo.save({'name': normalized_url})
        flash('Страница успешно добавлена', 'success')
        return redirect(url_for('urls_show', id=new_url_id))


@app.route('/urls')
def urls_show():
    with psycopg2.connect(os.getenv('DATABASE_URL')) as conn:
        repo = UrlRepository(conn)
        urls = repo.get_content()
        latest_checks = repo.get_latest_checks()

        urls_with_checks = []
        for url in urls:
            check = latest_checks.get(url['id'])
            urls_with_checks.append((url, check))

        return render_template('urls.html', urls_with_checks=urls_with_checks)


@app.route('/urls/<int:id>')
def show_url(id):
    with psycopg2.connect(os.getenv('DATABASE_URL')) as conn:
        repo = UrlRepository(conn)
        url, checks = repo.get_url_by_id(id)

        if url is None:
            flash('URL не найден', 'danger')
            return redirect(url_for('urls_show'))

        return render_template('url.html', url=url, checks=checks)


@app.post('/urls/<int:id>/checks')
def check_url(id):
    with psycopg2.connect(os.getenv('DATABASE_URL')) as conn:
        repo = UrlRepository(conn)
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
        except requests.RequestException as e:
            logging.error(f"Ошибка HTTP при проверке URL {url['name']}: {e}")
            flash('Произошла ошибка при проверке', 'danger')
        except Exception as e:
            logging.error(f"Ошибка при проверке URL: {e}")
            flash('Произошла ошибка при проверке', 'danger')

        return redirect(url_for('show_url', id=id))


if __name__ == '__main__':
    app.run(debug=False)
