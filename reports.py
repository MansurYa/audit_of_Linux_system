import sqlite3
from logger import db_lock
from config import config


def generate_statistics():
    """
    Генерирует статистику событий для отчетов.

    :return: dict: Словарь с количеством событий по типам.
    """
    with db_lock:
        conn = sqlite3.connect(config['db_path'])
        cursor = conn.cursor()
        cursor.execute('SELECT event_type, COUNT(*) FROM events GROUP BY event_type')
        data = cursor.fetchall()
        conn.close()

    return {event_type: count for event_type, count in data}
