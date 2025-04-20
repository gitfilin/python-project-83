import psycopg2
from psycopg2.extras import DictCursor


class UrlRepository:
    def __init__(self, conn):
        self.conn = conn # Сохраняем строку подключения


    def get_connection(self):
            """Создаёт и возвращает новое подключение к БД"""
            return psycopg2.connect(self.conn)  # Используем сохранённую строку


    def find_url(self, url):
        with self.conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute("SELECT * FROM urls WHERE name = %s", (url,))
            row = cur.fetchone()
            return dict(row) if row else None

    def save(self, url):
        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO urls (name) 
                VALUES (%s) 
                RETURNING id
            """, (url['name'],))
            self.conn.commit()
            return cur.fetchone()[0]

    def get_content(self):
        with self.conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute("""
                SELECT urls.id, urls.name, 
                       TO_CHAR(urls.created_at, 'YYYY-MM-DD') as created_at,
                       url_checks.status_code
                FROM urls
                LEFT JOIN (
                    SELECT DISTINCT ON (url_id) url_id, status_code
                    FROM url_checks
                    ORDER BY url_id, created_at DESC
                ) url_checks ON urls.id = url_checks.url_id
                ORDER BY urls.id DESC
            """)
            return [dict(row) for row in cur]

    def get_latest_checks(self):
        with self.conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute("""
                SELECT DISTINCT ON (url_id) 
                url_id, status_code, 
                TO_CHAR(created_at, 'YYYY-MM-DD') as created_at 
                FROM url_checks 
                ORDER BY url_id, created_at DESC
            """)
            return {row['url_id']: dict(row) for row in cur}

    def get_url_by_id(self, id):
        with self.conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute("SELECT * FROM urls WHERE id = %s", (id,))
            url = cur.fetchone()

            if not url:
                return None, None

            cur.execute("""
                SELECT id, status_code, h1, title, description,
                       TO_CHAR(created_at, 'YYYY-MM-DD') as created_at
                FROM url_checks 
                WHERE url_id = %s 
                ORDER BY created_at DESC
            """, (id,))
            checks = [dict(row) for row in cur.fetchall()]

            return dict(url), checks

    def save_check(self, url_id, check_data):
        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO url_checks 
                (url_id, status_code, h1, title, description) 
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
            """, (
                url_id,
                check_data['status_code'],
                check_data.get('h1', '')[:255],
                check_data.get('title', '')[:255],
                check_data.get('description', '')[:255]
            ))
            self.conn.commit()
            return cur.fetchone()[0]
