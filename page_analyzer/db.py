# db.py
import psycopg2
import os
from dotenv import load_dotenv

# Загружаем переменные из .env
load_dotenv()

def get_db_connection():
    """Возвращает соединение с базой данных"""
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    return conn