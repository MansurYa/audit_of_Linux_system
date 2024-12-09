import threading
from gui import AuditApp
from monitor import ProcessMonitor, FileMonitor, NetworkMonitor
from logger import init_db, rotate_logs


def main():
    """
    Главная функция для запуска приложения.
    """
    init_db()

    # Запуск ротации логов
    rotation_thread = threading.Thread(target=rotate_logs, daemon=True)
    rotation_thread.start()

    # Запуск мониторов
    process_monitor = ProcessMonitor()
    file_monitor = FileMonitor()
    network_monitor = NetworkMonitor()

    process_thread = threading.Thread(target=process_monitor.start_monitoring, daemon=True)
    file_thread = threading.Thread(target=file_monitor.start_monitoring, daemon=True)
    network_thread = threading.Thread(target=network_monitor.start_monitoring, daemon=True)

    process_thread.start()
    file_thread.start()
    network_thread.start()

    app = AuditApp()
    app.mainloop()


if __name__ == '__main__':
    main()
