import os
import time
import threading
import psutil
import pyinotify
import subprocess
from datetime import datetime
from logger import log_event
from config import config
import pwd
from notifier import send_email_notification
from concurrent.futures import ThreadPoolExecutor



class ProcessMonitor:
    def __init__(self):
        """
        Инициализация монитора процессов.
        """
        self.existing_pids = set()  # Набор текущих PID
        self.process_cache = {}  # Кэш для хранения информации о процессах
        self.lock = threading.Lock()  # Блокировка для синхронизации доступа к кэшу
        self.executor = ThreadPoolExecutor(max_workers=10)  # Пул потоков для запуска задач

    def start_monitoring(self):
        """
        Начинает мониторинг запуска и завершения процессов.
        """
        while True:
            current_pids = set(psutil.pids())  # Получение текущих PID
            new_pids = current_pids - self.existing_pids  # Новые процессы
            terminated_pids = self.existing_pids - current_pids  # Завершённые процессы

            # Отслеживаем новые процессы
            for pid in new_pids:
                self.executor.submit(self.trace_process, pid)  # Используем пул потоков

            # Обрабатываем завершённые процессы
            for pid in terminated_pids:
                self.handle_terminated_process(pid)

            # Обновляем список существующих PID
            self.existing_pids = current_pids

            # Очищаем кэш от неактуальных данных
            self.cleanup_cache()

            time.sleep(1)

    def trace_process(self, pid):
        """
        Отслеживает процесс.

        :param pid: int: PID процесса для отслеживания.
        """
        try:
            proc = psutil.Process(pid)
            user = proc.username()
            cmdline = ' '.join(proc.cmdline())
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            event_type = 'Process Started'
            description = f'Process {cmdline} (PID: {pid}) started by {user}'

            # Логируем событие
            log_event(timestamp, user, pid, event_type, description)

            # Сохраняем данные в кэш с блокировкой
            with self.lock:
                self.process_cache[pid] = {'user': user, 'cmdline': cmdline}

            # Отправка уведомления
            subject = f"Process Started: {cmdline}"
            body = f"Process {cmdline} (PID: {pid}) started by {user} at {timestamp}."
            send_email_notification(subject, body)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            # Если процесс уже завершён или недоступен, пропускаем
            pass

    def handle_terminated_process(self, pid):
        """
        Обрабатывает завершённый процесс.

        :param pid: int: PID завершённого процесса.
        """
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        event_type = 'Process Ended'

        # Извлекаем данные из кэша с блокировкой
        with self.lock:
            cached_data = self.process_cache.pop(pid, None)

        if cached_data:
            user = cached_data['user']
            cmdline = cached_data['cmdline']
            description = f'Process {cmdline} (PID: {pid}) ended.'
        else:
            user = 'Unknown'
            description = f'Process (PID: {pid}) ended.'

        # Логируем событие
        log_event(timestamp, user, pid, event_type, description)

    def cleanup_cache(self):
        """
        Удаляет из кэша неактуальные данные.
        """
        current_pids = set(psutil.pids())

        with self.lock:
            # Удаляем из кэша процессы, которые больше не существуют
            for pid in list(self.process_cache.keys()):  # Создаём копию ключей для безопасной итерации
                if pid not in current_pids:
                    del self.process_cache[pid]


class FileMonitor(pyinotify.ProcessEvent):
    def __init__(self):
        """
        Инициализация монитора файловой системы.
        """
        self.wm = pyinotify.WatchManager()
        self.notifier = pyinotify.Notifier(self.wm, self)
        mask = pyinotify.IN_MODIFY | pyinotify.IN_CREATE | pyinotify.IN_DELETE
        for path in config['monitor_paths']:
            self.wm.add_watch(path, mask, rec=True, auto_add=True)

    def process_IN_CREATE(self, event):
        """
        Обрабатывает событие создания файла или каталога.
        """
        self.log_event('File Created', event)

    def process_IN_DELETE(self, event):
        """
        Обрабатывает событие удаления файла или каталога.
        """
        self.log_event('File Deleted', event)

    def process_IN_MODIFY(self, event):
        """
        Обрабатывает событие изменения файла.
        """
        self.log_event('File Modified', event)

    def log_event(self, event_type, event):
        """
        Логирует событие файловой системы.

        :param event_type: str: Тип события.
        :param event: pyinotify.Event: Объект события.
        """
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        user = self.get_file_owner(event.pathname)
        description = event.pathname
        log_event(timestamp, user, None, event_type, description)

    def get_file_owner(self, filepath):
        """
        Получает имя пользователя-владельца файла.

        :param filepath: str: Путь к файлу.
        :return: str: Имя пользователя.
        """
        try:
            stat_info = os.stat(filepath)
            uid = stat_info.st_uid
            return pwd.getpwuid(uid).pw_name
        except FileNotFoundError:
            return 'Unknown'

    def start_monitoring(self):
        """
        Запускает мониторинг файловой системы.
        """
        self.notifier.loop()


class NetworkMonitor:
    def __init__(self):
        """
        Инициализация монитора сети.
        """
        self.existing_connections = {}

    def start_monitoring(self):
        """
        Начинает мониторинг сетевых соединений.
        """
        while True:
            connections = psutil.net_connections(kind='inet')
            current_connections = {
                (conn.laddr, conn.raddr): {'status': conn.status, 'pid': conn.pid}
                for conn in connections if conn.raddr
            }
            new_connections = current_connections.keys() - self.existing_connections.keys()
            terminated_connections = self.existing_connections.keys() - current_connections.keys()

            # Обрабатываем новые соединения
            for conn in new_connections:
                conn_data = current_connections[conn]
                pid = conn_data['pid']
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                event_type = 'Network Connection'

                # Получаем информацию о процессе
                try:
                    proc = psutil.Process(pid)
                    user = proc.username()
                    cmdline = ' '.join(proc.cmdline())
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    return

                description = f'{conn[0]} -> {conn[1]} (Status: {conn_data["status"]}, PID: {pid}, User: {user}, Command: {cmdline})'
                log_event(timestamp, user, pid, event_type, description)

            # Обрабатываем завершённые соединения
            for conn in terminated_connections:
                conn_data = self.existing_connections[conn]
                pid = conn_data['pid']
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                event_type = 'Connection Terminated'

                description = f'{conn[0]} -> {conn[1]} (Status: {conn_data["status"]}, PID: {pid})'
                log_event(timestamp, 'system', pid, event_type, description)

            # Обновляем список существующих соединений
            self.existing_connections = current_connections
            time.sleep(1)
