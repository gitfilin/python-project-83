import os

from dotenv import load_dotenv
from flask import Flask, flash, redirect, render_template, request, url_for
from psycopg2.extras import NamedTupleCursor
import validators
import requests
from bs4 import BeautifulSoup

from .db import get_db_connection
from .normalizer import normalize_url


load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')


@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')


@app.route('/urls', methods=['POST'])
def urls_create():
    """Обработка формы добавления нового URL"""
    raw_url = request.form.get('url', '').strip()

    if not validators.url(raw_url) or len(raw_url) > 255:
        flash('Некорректный URL-адрес', 'danger')
        return render_template('index.html', raw_url=raw_url), 422

    name = normalize_url(raw_url)

    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=NamedTupleCursor)

    try:
        cur.execute(
            """
            SELECT id
            FROM urls
            WHERE name = %s
            """,
            (name,),
        )
        existing_url = cur.fetchone()

        if existing_url:
            url_id = existing_url.id
            flash('Страница уже существует', 'info')
        else:
            cur.execute(
                """
                INSERT INTO urls (name)
                VALUES (%s)
                RETURNING id
                """,
                (name,),
            )
            url_id = cur.fetchone().id
            conn.commit()
            flash('Страница успешно добавлена', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'Ошибка: {e}', 'danger')
        return redirect(url_for('index'))
    finally:
        cur.close()
        conn.close()

    return redirect(url_for('show_url', id=url_id))


@app.route('/urls')
def urls_list():
    """Показываем все URL и их последние проверки"""
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=NamedTupleCursor)

    cur.execute(
        """
        SELECT
            urls.id,
            urls.name,
            urls.created_at,
            last_check.created_at AS last_check_at,
            last_check.status_code AS last_status_code
        FROM urls
        LEFT JOIN LATERAL (
            SELECT id, status_code, created_at
            FROM url_checks
            WHERE url_checks.url_id = urls.id
            ORDER BY created_at DESC, id DESC
            LIMIT 1
        ) AS last_check ON TRUE
        ORDER BY urls.created_at DESC, urls.id DESC
        """
    )
    urls = cur.fetchall()
    cur.close()
    conn.close()

    return render_template('urls.html', urls=urls)


@app.route('/urls/<int:id>')
def show_url(id):
    """Показываем информацию об одном URL и его проверки"""
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=NamedTupleCursor)

    cur.execute(
        """
        SELECT id, name, created_at
        FROM urls
        WHERE id = %s
        """,
        (id,),
    )
    url = cur.fetchone()

    if not url:
        cur.close()
        conn.close()
        flash('URL не найден', 'warning')
        return redirect(url_for('urls_list'))

    cur.execute(
        """
        SELECT id, status_code, h1, title, description, created_at
        FROM url_checks
        WHERE url_id = %s
        ORDER BY created_at DESC, id DESC
        """,
        (id,),
    )
    checks = cur.fetchall()

    cur.close()
    conn.close()

    return render_template('url.html', url=url, checks=checks)


@app.route('/urls/<int:id>/checks', methods=['POST'])
def urls_check(id):
    """Запускает проверку указанного URL"""
    conn = get_db_connection()
    cur = conn.cursor(cursor_factory=NamedTupleCursor)

    cur.execute(
        """
        SELECT id, name
        FROM urls
        WHERE id = %s
        """,
        (id,),
    )
    url = cur.fetchone()

    if not url:
        cur.close()
        conn.close()
        flash('URL не найден', 'warning')
        return redirect(url_for('urls_list'))

    try:
        target_url = url.name
        if not target_url.startswith(('http://', 'https://')):
            target_url = f'http://{target_url}'

        response = requests.get(target_url)
        response.raise_for_status()
        status_code = response.status_code

        soup = BeautifulSoup(response.text, 'html.parser')

        h1_tag = soup.find('h1')
        h1 = h1_tag.get_text(strip=True) if h1_tag else ''

        title_tag = soup.find('title')
        title = title_tag.get_text(strip=True) if title_tag else ''

        description = ''
        meta_description = soup.find('meta', attrs={'name': 'description'})
        if meta_description and meta_description.get('content'):
            description = meta_description['content'][:255]

        cur.execute(
            """
            INSERT INTO url_checks (url_id, status_code, h1, title, description)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (id, status_code, h1, title, description),
        )
        conn.commit()
        flash('Страница успешно проверена', 'success')
    except requests.RequestException:
        conn.rollback()
        flash('Произошла ошибка при проверке', 'danger')
    finally:
        cur.close()
        conn.close()

    return redirect(url_for('show_url', id=id))


@app.errorhandler(404)
def page_not_found(e):
    return render_template('404_page.html'), 404