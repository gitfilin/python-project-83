from flask import Flask, render_template, request, redirect, url_for, flash
import validators
from urllib.parse import urlparse
import psycopg2
import requests
import os
from dotenv import load_dotenv
from page_analyzer.url_repository import UrlRepository
from page_analyzer.parser import get_data

load_dotenv()


app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['DATABASE_URL'] = os.getenv('DATABASE_URL')

db = UrlRepository(app.config['DATABASE_URL'])


# Проверка
try:
    conn = db.get_connection()
    print("✅ Подключение успешно!")
    conn.close()
except psycopg2.Error as e:
    print(f"❌ Ошибка подключения: {e}")


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


@app.route('/urls/<int:id>/checks', methods=['POST'])
def create_check(id):
    with psycopg2.connect(os.getenv('DATABASE_URL')) as conn:
        repo = UrlRepository(conn)
        url_data = repo.get_url_by_id(id)

        if not url_data or not url_data[0]:
            flash('URL не найден', 'danger')
            return redirect(url_for('urls'))

        url = url_data[0]

        try:

            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(url['name'],
                                    timeout=10,
                                    headers=headers,
                                    allow_redirects=True)
            response.raise_for_status()

            # Проверяем content-type перед парсингом
            content_type = response.headers.get('content-type', '')
            if 'text/html' not in content_type:
                flash('Страница не является HTML-документом', 'warning')
                return redirect(url_for('url_details', id=id))

            soup = get_data(response.text, 'html.parser')

            def safe_extract(element, attr=None):
                if not element:
                    return ''
                try:
                    if attr:
                        return element.get(attr, '').strip()
                    return element.get_text().strip()
                except Exception:
                    return ''

            h1 = safe_extract(soup.find('h1'))
            title = safe_extract(soup.find('title'))
            description = safe_extract(
                soup.find('meta', attrs={'name': 'description'}),
                'content'
            )

            check_data = {
                'status_code': response.status_code,
                'h1': h1,
                'title': title,
                'description': description
            }

            repo.save_check(id, check_data)
            flash('Страница успешно проверена', 'success')

        except requests.exceptions.Timeout:
            flash('Проверка заняла слишком много времени', 'danger')
        except requests.exceptions.HTTPError as e:
            flash(
                f'Ошибка HTTP при проверке: {e.response.status_code}', 'danger')
        except requests.exceptions.RequestException as e:
            flash(f'Ошибка при проверке: {str(e)}', 'danger')
        except Exception as e:
            app.logger.error(f'Unexpected error: {str(e)}')
            flash('Произошла непредвиденная ошибка при проверке', 'danger')

        return redirect(url_for('url_details', id=id))


if __name__ == '__main__':
    app.run(debug=False)
