import psycopg2
from psycopg2.extras import DictCursor


class UrlRepository:
    def __init__(self, conn):
        self.conn = conn

    def get_connection(self):
        return psycopg2.connect(self.conn)

    def get_content(self):
        """Получаем все данные из БД вместе с последними проверками"""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=DictCursor) as cur:
                cur.execute("""
                    SELECT 
                        urls.id,
                        urls.name,
                        urls.created_at,
                        COALESCE(last_check.status_code::text, '') as last_status_code,
                        COALESCE(TO_CHAR(last_check.created_at, 'DD-MM-YYYY'), '') as last_check_date
                    FROM urls
                    LEFT JOIN LATERAL (
                        SELECT status_code, created_at
                        FROM url_checks
                        WHERE url_checks.url_id = urls.id
                        ORDER BY created_at DESC
                        LIMIT 1
                    ) last_check ON true
                    ORDER BY urls.id DESC
                """)
                return [dict(row) for row in cur]

    def find_url(self, url):
        """Ищет URL в базе данных и возвращает его, если найден."""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=DictCursor) as cur:
                cur.execute(
                    "SELECT id, name, created_at FROM urls WHERE name = %s", (url,))
                row = cur.fetchone()
                return dict(row) if row else None

    def save(self, url):
        """Сохраняет URL в БД и возвращает его id."""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO urls (name) VALUES (%s) RETURNING id",
                    (url['name'],)
                )
                new_id = cur.fetchone()[0]
            conn.commit()
        return new_id

    def get_url_by_id(self, id):
        """Получает URL и его проверки по ID."""
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=DictCursor) as cur:
                # Получаем информацию об URL
                cur.execute('''
                    SELECT id, name, TO_CHAR(created_at, 'YYYY-MM-DD') as created_at
                    FROM urls WHERE id = %s
                ''', (id,))
                url = cur.fetchone()

                if url is None:
                    return None, None

                # Получаем все проверки для данного URL
                cur.execute('''
                    SELECT id, status_code, h1, title, description,
                           TO_CHAR(created_at, 'DD-MM-YYYY') as created_at
                    FROM url_checks
                    WHERE url_id = %s
                    ORDER BY id DESC
                ''', (id,))
                checks = cur.fetchall()

                return dict(url), [dict(check) for check in checks]

    def _update(self, url):
        with self.conn.cursor() as cur:
            cur.execute(
                "UPDATE urls SET manufacturer = %s, model = %s WHERE id = %s",
                (url['manufacturer'], url['model'], url['id'])
            )
        self.conn.commit()

    def _create(self, url):
        with self.conn.cursor() as cur:
            cur.execute(
                "INSERT INTO urls (name) VALUES (%s) RETURNING id",
                (url['name'],)  # Передаем корректное значение
            )
            url['id'] = cur.fetchone()[0]  # Получаем ID и сохраняем в словаре
        self.conn.commit()  # Подтверждаем изменения

    def save_check(self, url_id, check_data):
        """Сохраняет результаты проверки URL в базу данных."""
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute('''
                    INSERT INTO url_checks (url_id, status_code, h1, title, description)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id
                ''', (
                    url_id,
                    check_data.get('status_code'),
                    check_data.get('h1'),
                    check_data.get('title'),
                    check_data.get('description')
                ))
                check_id = cur.fetchone()[0]
            conn.commit()
        return check_id
