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


class ProcessMonitor:
    def __init__(self):
        """
        Инициализация монитора процессов.
        """
        self.existing_pids = set()

    def start_monitoring(self):
        """
        Начинает мониторинг запуска и завершения процессов с использованием `ptrace`.
        """
        while True:
            current_pids = set(psutil.pids())
            new_pids = current_pids - self.existing_pids
            terminated_pids = self.existing_pids - current_pids

            for pid in new_pids:
                threading.Thread(target=self.trace_process, args=(pid,), daemon=True).start()

            for pid in terminated_pids:
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                event_type = 'Process Ended'
                description = f'Process (PID: {pid}) ended.'
                log_event(timestamp, 'Unknown', pid, event_type, description)

            self.existing_pids = current_pids
            time.sleep(1)

    def trace_process(self, pid):
        """
        Использует ptrace для отслеживания процесса.

        :param pid: int: PID процесса для отслеживания.
        """
        try:
            proc = psutil.Process(pid)
            user = proc.username()
            cmdline = ' '.join(proc.cmdline())
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            event_type = 'Process Started'
            description = f'Process {cmdline} (PID: {pid}) started by {user}'
            log_event(timestamp, user, pid, event_type, description)

            # Отправка уведомления по электронной почте
            subject = f"Process Started: {cmdline}"
            body = f"Process {cmdline} (PID: {pid}) started by {user} at {timestamp}."
            send_email_notification(subject, body)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return


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
        self.existing_connections = set()

    def start_monitoring(self):
        """
        Начинает мониторинг сетевых соединений.
        """
        while True:
            connections = psutil.net_connections(kind='inet')
            current_connections = set((conn.laddr, conn.raddr, conn.status) for conn in connections if conn.raddr)
            new_connections = current_connections - self.existing_connections

            for conn in new_connections:
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                event_type = 'Network Connection'
                description = f'{conn[0]} -> {conn[1]} (Status: {conn[2]})'
                log_event(timestamp, 'system', None, event_type, description)

            self.existing_connections = current_connections
            time.sleep(1)
