import os
import psycopg2
from flask import Flask, render_template, request, redirect, url_for, flash
from dotenv import load_dotenv
from psycopg2.extras import DictCursor
from urllib.parse import urlparse
import validators

load_dotenv()  # загружает переменные окружения из .env файла

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv(
    'SECRET_KEY')  # получает значение из окружения

DATABASE_URL = os.getenv('DATABASE_URL')


def get_connection():
    return psycopg2.connect(DATABASE_URL)


@app.route('/')
def index():
    return render_template('index.html')


@app.post('/urls')
def add_url():
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
            cur.execute(
                'INSERT INTO urls (name) VALUES (%s) RETURNING id',
                (normalized_url,)
            )
            url_id = cur.fetchone()[0]
            conn.commit()

    flash('Страница успешно добавлена', 'success')
    return redirect(url_for('show_url', id=url_id))


@app.route('/urls/<int:id>')
def show_url(id):
    with get_connection() as conn:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute('SELECT * FROM urls WHERE id = %s', (id,))
            url = cur.fetchone()
    return render_template('url.html', url=url)


@app.route('/urls')
def urls_list():
    with get_connection() as conn:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute('SELECT * FROM urls ORDER BY created_at DESC')
            urls = cur.fetchall()
    return render_template('urls.html', urls=urls)


if __name__ == '__main__':
    app.run(debug=True)
