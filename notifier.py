import smtplib
from email.mime.text import MIMEText
from config import config


def send_email_notification(subject, body):
    """
    Отправляет уведомление по электронной почте.

    :param subject: str: Тема письма.
    :param body: str: Тело письма.
    """
    if not config['email_notifications']:
        return

    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = config['smtp_user']
    msg['To'] = ', '.join(config['email_recipients'])

    try:
        with smtplib.SMTP(config['smtp_server'], config['smtp_port']) as server:
            server.starttls()
            server.login(config['smtp_user'], config['smtp_password'])
            server.send_message(msg)
    except Exception as e:
        print(f"Failed to send email notification: {e}")
