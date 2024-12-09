import json


def load_config():
    """
    Загружает конфигурацию из файла config.json.

    :return: dict: Словарь с параметрами конфигурации.
    """
    with open('config.json', 'r') as file:
        return json.load(file)


config = load_config()
