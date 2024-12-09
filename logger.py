import sqlite3
import threading
from datetime import datetime, timedelta
from config import config
import time


db_lock = threading.Lock()


def init_db():
    """
    Инициализирует базу данных для хранения событий.
    """
    with db_lock:
        conn = sqlite3.connect(config["db_path"])
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                user TEXT,
                pid INTEGER,
                event_type TEXT,
                description TEXT
            )
        ''')
        conn.commit()
        conn.close()


def log_event(timestamp, user, pid, event_type, description):
    """
    Сохраняет событие в базу данных.

    :param timestamp: str: Время события.
    :param user: str: Пользователь, связанный с событием.
    :param pid: int: PID процесса (если применимо).
    :param event_type: str: Тип события.
    :param description: str: Описание события.
    """
    with db_lock:
        conn = sqlite3.connect(config['db_path'])
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO events (timestamp, user, pid, event_type, description)
            VALUES (?, ?, ?, ?, ?)
        ''', (timestamp, user, pid, event_type, description))
        conn.commit()
        conn.close()


def rotate_logs():
    """
    Удаляет старые записи из базы данных для предотвращения переполнения.
    """
    while True:
        with db_lock:
            conn = sqlite3.connect(config['db_path'])
            cursor = conn.cursor()
            cutoff_date = (datetime.now() - timedelta(days=config['log_rotation_days'])).strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute('DELETE FROM events WHERE timestamp < ?', (cutoff_date,))
            conn.commit()
            conn.close()
        time.sleep(86400)  # Проверяет раз в сутки


