import tkinter as tk
from tkinter import ttk, messagebox
from logger import db_lock
import sqlite3
from config import config
from reports import generate_statistics
from datetime import datetime
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg


class AuditApp(tk.Tk):
    def __init__(self):
        """
        Инициализация графического интерфейса приложения.
        """
        super().__init__()
        self.title("Системный аудит")
        self.geometry("1000x600")
        self.create_widgets()

    def create_widgets(self):
        """
        Создает виджеты интерфейса.
        """
        # Фрейм для фильтров
        filter_frame = ttk.Frame(self)
        filter_frame.pack(side=tk.TOP, fill=tk.X)

        ttk.Label(filter_frame, text="Пользователь:").grid(row=0, column=0, padx=5, pady=5)
        self.user_var = tk.StringVar()
        ttk.Entry(filter_frame, textvariable=self.user_var).grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(filter_frame, text="Тип события:").grid(row=0, column=2, padx=5, pady=5)
        self.event_type_var = tk.StringVar()
        event_types = ["", "Process Started", "Process Ended", "File Created", "File Deleted", "File Modified", "Network Connection", "System Event"]
        ttk.Combobox(filter_frame, textvariable=self.event_type_var, values=event_types).grid(row=0, column=3, padx=5, pady=5)

        ttk.Label(filter_frame, text="Дата (YYYY-MM-DD):").grid(row=0, column=4, padx=5, pady=5)
        self.date_var = tk.StringVar()
        ttk.Entry(filter_frame, textvariable=self.date_var).grid(row=0, column=5, padx=5, pady=5)

        ttk.Button(filter_frame, text="Поиск", command=self.search_events).grid(row=0, column=6, padx=5, pady=5)

        # Таблица с результатами
        self.tree = ttk.Treeview(self, columns=('timestamp', 'user', 'pid', 'event_type', 'description'), show='headings')
        self.tree.heading('timestamp', text='Время')
        self.tree.heading('user', text='Пользователь')
        self.tree.heading('pid', text='PID')
        self.tree.heading('event_type', text='Тип события')
        self.tree.heading('description', text='Описание')
        self.tree.pack(fill=tk.BOTH, expand=True)

        # Кнопки управления
        btn_frame = ttk.Frame(self)
        btn_frame.pack(side=tk.BOTTOM, fill=tk.X)

        ttk.Button(btn_frame, text="Обновить", command=self.load_events).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(btn_frame, text="Генерировать отчет", command=self.show_report).pack(side=tk.LEFT, padx=5, pady=5)

        # Первичная загрузка событий
        self.load_events()

    def load_events(self):
        """
        Загружает события из базы данных и отображает их в таблице.
        """
        for row in self.tree.get_children():
            self.tree.delete(row)

        with db_lock:
            conn = sqlite3.connect(config['db_path'])
            cursor = conn.cursor()
            cursor.execute('SELECT timestamp, user, pid, event_type, description FROM events ORDER BY id DESC LIMIT 100')
            for row in cursor.fetchall():
                self.tree.insert('', tk.END, values=row)
            conn.close()

    def search_events(self):
        """
        Ищет события по заданным критериям и отображает результаты.
        """
        user = self.user_var.get()
        event_type = self.event_type_var.get()
        date = self.date_var.get()

        query = 'SELECT timestamp, user, pid, event_type, description FROM events WHERE 1=1'
        params = []

        if user:
            query += ' AND user LIKE ?'
            params.append(f'%{user}%')
        if event_type:
            query += ' AND event_type = ?'
            params.append(event_type)
        if date:
            try:
                datetime.strptime(date, '%Y-%m-%d')
                query += ' AND date(timestamp) = ?'
                params.append(date)
            except ValueError:
                messagebox.showerror("Ошибка", "Неверный формат даты. Используйте YYYY-MM-DD.")
                return

        with db_lock:
            conn = sqlite3.connect(config['db_path'])
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            conn.close()

        for row in self.tree.get_children():
            self.tree.delete(row)

        for row in rows:
            self.tree.insert('', tk.END, values=row)

    def show_report(self):
        """
        Отображает отчет в новом окне.
        """
        data = generate_statistics()
        if not data:
            messagebox.showinfo("Отчет", "Нет данных для отчета.")
            return

        event_types = list(data.keys())
        counts = list(data.values())

        # Увеличиваем размер графика
        fig, ax = plt.subplots(figsize=(8, 6))  # Размеры графика увеличены для видимости
        ax.bar(event_types, counts)
        ax.set_xlabel('Тип события')
        ax.set_ylabel('Количество')
        ax.set_title('Статистика событий')

        # Поворачиваем подписи на оси X
        ax.tick_params(axis='x', rotation=45)

        # Увеличиваем отступы
        plt.tight_layout()  # Автоматическая корректировка отступов

        # Отображение графика в Tkinter
        top = tk.Toplevel(self)
        top.title("Отчет")

        canvas = FigureCanvasTkAgg(fig, master=top)
        canvas.get_tk_widget().pack()
        canvas.draw()
