#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Скрипт выводит рейтинг TF-IDF указанного текста, показывает схожие работы.
# Нуждается в текстовом корпусе от gen_database.

import os
import sys
import argparse
import sqlite3
from profiler_config import *
from gen_database import correct_path
from gen_database import dict_sort
from gen_database import txt_to_dict
from gen_database import tf_idf
from gen_database import gen_tokens_dict
from gen_database import load_tokens_dict
from gen_database import create_linkscloud
from database_search import get_bookdata

#-------------------------------------------------------------------------
# Функции:

def create_parser():
    """Список доступных параметров скрипта."""
    parser = argparse.ArgumentParser()
    parser.add_argument('file',
                        action='store', type=str, nargs='*', default='',
                        help='Текстовый файл'
                        )
    parser.add_argument('-l', '--links',
                        action='store_true', default='False',
                        help='Вывод таблицы схожих текстов'
                        )
    parser.add_argument('-o', '--output',
                        action='store_true', default='False',
                        help='Вывод таблицы TF-IDF слов рассказа'
                        )
    parser.add_argument('-L' '--lines',
                        action='store', dest='output_lines', type=int, default=OUTPUT_LINES,
                        help='Число строк в выводе.'
                        )
    parser.add_argument('-D', '--database',
                        action='store', dest='database', type=str, default=DATABASE_PATH,
                        help='Путь к другой базе данных'
                        )
    return parser

def output_score(local_dict, tokens_dict, filename,
        database_path=DATABASE_PATH, output_max=20):
    """Вывод рейтинга TF-IDF."""
    database = sqlite3.connect(database_path)
    cursor = database.cursor()
    score_dict = tf_idf(local_dict, tokens_dict)
    n = 0
    for word, value in dict_sort(score_dict).items():
        book, author = get_bookdata(filename, cursor)
        if n < output_max:
            n = n + 1
            print ('{0:3} {1:10} | {2:30} | {3}'.format(n, round(value),
                word, author))
        else:
            break

def output_links(local_dict, tokens_dict, filename,
        database_path=DATABASE_PATH, output_max=20):
    """Вывод похожих текстов."""
    database = sqlite3.connect(database_path)
    cursor = database.cursor()
    score_dict = tf_idf(local_dict, tokens_dict)
    cloud = create_linkscloud(score_dict, tokens_dict)
    n = 0
    for filename, value in dict_sort(cloud).items():
        book, author = get_bookdata(filename, cursor)
        # Вывод в процентах:
        value = round(value * 100, 5)
        if value > 0.1 and n < output_max:
            n = n + 1
            print ('{0:2} {1:10} | {3:30} | {2}'.format(n, round(value, 3),
                book, author))
        else:
            break

#-------------------------------------------------------------------------
# Тело программы:

if __name__ == '__main__':
    # Создаётся список аргументов скрипта:
    parser = create_parser()
    namespace = parser.parse_args()
    # Уточняем пути к базе данных и основному словарю:
    database_path, tokens_path = correct_path(namespace.database)
    # Загружаем основной словарь:
    tokens_dict = load_tokens_dict(database_path, tokens_path)
    # Проверяем, существует ли указанный файл:
    if namespace.file:
        file_path = namespace.file[0]
        if os.path.exists(file_path):
            filename = os.path.basename(file_path)
            file = open(file_path, "r")
            text = file.read()
            file.close()
    # Если нет, читаем стандартный ввод:
    else:
        filename = 'stdin'
        text = sys.stdin.read()
    # Обрабатываем текст, преобразуем в словарь:
    text_dict = txt_to_dict(text)
    local_dict = text_dict['phrasefreq']
    local_dict.update(text_dict['wordfreq'])
    # Выводим данные:
    if namespace.links is True:
        output_links(local_dict, tokens_dict, filename,
                database_path, namespace.output_lines)
    elif namespace.output is True:
        output_score(local_dict, tokens_dict, filename,
                database_path, namespace.output_lines)
    else:
        # Исправить
        # Хау, сделай извлечение токенов из текста. Это же ключевое.
        output_links(local_dict, tokens_dict, filename,
                database_path, namespace.output_lines)
