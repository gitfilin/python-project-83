import psycopg2
from psycopg2.extras import DictCursor


class UrlRepository:
    def __init__(self, conn):
        self.conn = conn

    def get_connection(self):
        return psycopg2.connect(self.conn)

    def get_content(self):
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=DictCursor) as cur:
                cur.execute("SELECT * FROM urls ORDER BY id DESC")
                return [dict(row) for row in cur]

    def find(self, normalized_url):
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=DictCursor) as cur:
                cur.execute('SELECT * FROM urls WHERE name = %s',
                        (normalized_url,))
                row = cur.fetchone()
                return dict(row) if row else None
            
    def save(self, user_data):
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                if 'id' not in user_data:
                    # New user
                    cur.execute(
                        "INSERT INTO users (name, email) VALUES (%s, %s) RETURNING id",
                        (user_data['name'], user_data['email'])
                    )
                    user_data['id'] = cur.fetchone()[0]
                else:
                    # Existing user
                    cur.execute(
                        "UPDATE users SET name = %s, email = %s WHERE id = %s",
                        (user_data['name'],
                         user_data['email'], user_data['id'])
                    )
            conn.commit()
        return user_data['id']

    def destroy(self, id):
        with self.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM users WHERE id = %s", (id,))
            conn.commit()
