# Импортируем библиотеку psycopg2 для работы с PostgreSQL
import psycopg2
# Импортируем DictCursor из psycopg2.extras для работы с результатами запросов как со словарями
from psycopg2.extras import DictCursor


# Создаем класс UrlRepository для работы с URL в базе данных
class UrlRepository:
    # Инициализируем класс, принимая соединение с базой данных
    def __init__(self, conn):
        self.conn = conn  # Сохраняем соединение с БД как атрибут класса

    # Метод для получения всех URL из таблицы
    def get_content(self):
        """Получаем все данные из таблицы urls"""
        # Создаем курсор с фабрикой DictCursor (возвращает строки как словари)
        with self.conn.cursor(cursor_factory=DictCursor) as cur:
            # Выполняем SQL-запрос для получения всех URL
            cur.execute("""
                SELECT id, name,
                       TO_CHAR(created_at, 'YYYY-MM-DD') as created_at
                FROM urls
                ORDER BY id DESC
            """)
            # Преобразуем результат в список словарей и возвращаем
            return [dict(row) for row in cur]

    # Метод для поиска URL в базе данных
    def find_url(self, url):
        """Ищет URL в базе данных и возвращает его, если найден."""
        with self.conn.cursor(cursor_factory=DictCursor) as cur:
            # Выполняем запрос на поиск URL по имени
            cur.execute("""
                SELECT id, name,
                       TO_CHAR(created_at, 'YYYY-MM-DD') as created_at
                FROM urls
                WHERE name = %s
            """, (url,))
            # Получаем одну строку результата
            row = cur.fetchone()
            # Возвращаем как словарь, если URL найден, иначе None
            return dict(row) if row else None

    # Метод для сохранения нового URL в базу данных
    def save(self, url):
        """Сохраняет URL в БД и возвращает его id."""
        with self.conn.cursor() as cur:
            # Вставляем новый URL и возвращаем его ID
            cur.execute("""
                INSERT INTO urls (name)
                VALUES (%s)
                RETURNING id
            """, (url['name'],))
            # Получаем ID новой записи
            new_id = cur.fetchone()[0]
            # Фиксируем изменения в БД
            self.conn.commit()
            return new_id

    # Метод для получения URL и его проверок по ID
    def get_url_by_id(self, id):
        """Получает URL и его проверки по ID."""
        with self.conn.cursor(cursor_factory=DictCursor) as cur:
            # Получаем информацию об URL по его ID
            cur.execute("""
                SELECT id, name,
                       TO_CHAR(created_at, 'YYYY-MM-DD') as created_at
                FROM urls
                WHERE id = %s
            """, (id,))
            url = cur.fetchone()  # Получаем одну запись

            # Если URL не найден, возвращаем None для обоих значений
            if url is None:
                return None, None

            # Получаем все проверки для данного URL
            cur.execute("""
                SELECT id, status_code, h1, title, description,
                       TO_CHAR(created_at, 'YYYY-MM-DD') as created_at
                FROM url_checks
                WHERE url_id = %s
                ORDER BY id DESC
            """, (id,))
            checks = cur.fetchall()  # Получаем все записи проверок

            # Возвращаем URL как словарь и список проверок (каждая проверка - словарь)
            return dict(url), [dict(check) for check in checks]

    # Метод для сохранения результатов проверки URL
    def save_check(self, url_id, check_data):
        """Сохраняет результаты проверки URL в базу данных."""
        with self.conn.cursor() as cur:
            # Вставляем данные проверки в таблицу url_checks
            cur.execute("""
                INSERT INTO url_checks
                (url_id, status_code, h1, title, description)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
            """, (
                url_id,
                check_data.get('status_code'),  # Код статуса HTTP
                # Заголовок h1, обрезанный до 255 символов
                check_data.get('h1', '')[:255],
                # Заголовок страницы, обрезанный
                check_data.get('title', '')[:255],
                check_data.get('description', '')[:255]  # Описание, обрезанное
            ))
            # Получаем ID новой проверки
            check_id = cur.fetchone()[0]
            # Фиксируем изменения
            self.conn.commit()
            return check_id

    # Метод для получения последних проверок всех URL
    def get_latest_checks(self):
        """Получает последние проверки для всех URL"""
        with self.conn.cursor(cursor_factory=DictCursor) as cur:
            # Используем DISTINCT ON для получения последней проверки каждого URL
            cur.execute("""
                            SELECT DISTINCT ON (url_id)
                            url_id, status_code, TO_CHAR(created_at, 'YYYY-MM-DD') as created_at
                            FROM url_checks
                            ORDER BY url_id, created_at DESC
                            """)
            # Возвращаем словарь, где ключ - url_id, значение - данные проверки
            return {row['url_id']: dict(row) for row in cur}
