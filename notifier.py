import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from config import config


def send_email_notification(subject, body, is_html=False):
    """
    Отправляет уведомление по электронной почте.

    :param subject: str: Тема письма.
    :param body: str: Тело письма.
    :param is_html: bool: Указывает, является ли тело письма HTML. По умолчанию False.
    """
    if not config.get('email_notifications', False):
        return

    smtp_server = config.get('smtp_server')
    smtp_port = config.get('smtp_port')
    smtp_user = config.get('smtp_user')
    smtp_password = config.get('smtp_password')
    email_recipients = config.get('email_recipients')

    # Проверка параметров конфигурации
    if not smtp_server or not smtp_port or not smtp_user or not smtp_password or not email_recipients:
        print("Некоторые параметры SMTP не указаны в конфигурации.")
        return

    # Создание сообщения
    msg = MIMEMultipart()
    msg['Subject'] = subject
    msg['From'] = smtp_user
    msg['To'] = ', '.join(email_recipients)

    # Добавляем текст в зависимости от формата
    if is_html:
        msg.attach(MIMEText(body, 'html'))
    else:
        msg.attach(MIMEText(body, 'plain'))

    try:
        # Подключение к SMTP-серверу
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()  # Включаем шифрование TLS
            server.login(smtp_user, smtp_password)  # Логинимся
            server.send_message(msg)  # Отправляем сообщение
            print(f"Email успешно отправлен: {email_recipients}")

    except Exception as e:
        print(f"Ошибка при отправке email: {e}")


if __name__ == "__main__":
    subject = "Тестовое уведомление"
    body = "Это тестовое сообщение."
    send_email_notification(subject, body)
