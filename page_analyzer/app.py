from flask import Flask, render_template, request, redirect, url_for, flash
import validators
from urllib.parse import urlparse
import psycopg2
from psycopg2.extras import DictCursor
from bs4 import BeautifulSoup
import requests
import os
from dotenv import load_dotenv
from page_analyzer.url_repository import UrlRepository
from page_analyzer.parser import get_data

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')


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
    except Exception:
        flash('Некорректный URL', 'danger')
        return render_template('index.html', raw_url=raw_url), 422

    with psycopg2.connect(os.getenv('DATABASE_URL')) as conn:
        repo = UrlRepository(conn)
        existing_url = repo.find_url(normalized_url)

        if existing_url:
            flash('Страница уже существует', 'info')
            return redirect(url_for('url_details', id=existing_url['id']))

        new_url_id = repo.save({'name': normalized_url})
        flash('Страница успешно добавлена', 'success')
        return redirect(url_for('url_details', id=new_url_id))


@app.route('/urls')
def urls():
    with psycopg2.connect(os.getenv('DATABASE_URL')) as conn:
        repo = UrlRepository(conn)
        urls = repo.get_content()
        latest_checks = repo.get_latest_checks()

        urls_with_checks = []
        for url in urls:
            check = latest_checks.get(url['id'])
            urls_with_checks.append((url, check))

        return render_template('urls.html', urls=urls_with_checks)


@app.route('/urls/<int:id>')
def url_details(id):
    with psycopg2.connect(os.getenv('DATABASE_URL')) as conn:
        repo = UrlRepository(conn)
        url, checks = repo.get_url_by_id(id)

        if url is None:
            flash('URL не найден', 'danger')
            return redirect(url_for('urls'))

        return render_template('url.html', url=url, checks=checks)


@app.post('/urls/<int:id>/checks')
def url_checks(id):
    with psycopg2.connect(os.getenv('DATABASE_URL')) as conn:
        repo = UrlRepository(conn)
        url = repo.get_url_by_id(id)

        if not url or not url[0]:
            flash('URL не найден', 'danger')
            return redirect(url_for('urls'))

        try:
            # Основная проверка URL
            response = requests.get(url[0]['name'], timeout=5)
            response.raise_for_status()

            # Получаем и подготавливаем данные
            parsed_data = get_data(response.text)
            check_data = {
                'url_id': id,
                'status_code': response.status_code,
                'title': parsed_data.get('title', ''),
                'h1': parsed_data.get('h1', ''),
                'description': parsed_data.get('description', '')
            }

            # Сохраняем в БД
            repo.save_check(id, check_data)
            flash('Страница успешно проверена', 'success')

        except requests.Timeout:
            flash('Превышено время ожидания ответа', 'danger')
        except requests.HTTPError as e:
            flash(f'Ошибка HTTP: {e.response.status_code}', 'danger')
        except requests.RequestException:
            flash('Произошла ошибка при проверке', 'danger')
        except Exception as e:
            app.logger.error(f'Check failed: {str(e)}')
            flash('Внутренняя ошибка сервера', 'danger')

        return redirect(url_for('url_details', id=id))


if __name__ == '__main__':
    app.run(debug=False)
