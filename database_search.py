#!/usr/bin/env python
# -*- coding: utf-8 -*-


import os
import argparse
import sqlite3
import pickle
import collections

# Из местных скриптов:
import wordfreq_morph
from profiler_config import *
from gen_database import dict_sort
from gen_database import metadict_path

#-------------------------------------------------------------------------
# Функции:

def create_parser():
    """Список доступных параметров скрипта."""
    parser = argparse.ArgumentParser()
    parser.add_argument('search_string',
                        action='store', type=str, nargs='*', default='',
                        help='Поиск в базе данных (Янтарь, Янт, yantar)'
                        )
    parser.add_argument('-l', '--links',
                        action='store_true', default='False',
                        help='Вывод таблицы схожих текстов'
                        )
    parser.add_argument('-p', '--phrases',
                        action='store_true', default='False',
                        help='Вывод характерных для автора слов/фраз'
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

def get_bookdata(filename, cursor):
    book_data = cursor.execute("SELECT book_title,author\
            FROM stories WHERE filename=?"\
            ,(filename,)).fetchone()
    book = book_data[0]
    author = book_data[1]
    if book == 'None':
        book = filename
    if author == 'None':
        author = filename
    return book, author

def get_blob(search_string, table, cursor):
    search_string = ' '.join(search_string)
    search_string = '%' + search_string + '%'
    blob_list = cursor.execute(
            "SELECT filename, " + table + " FROM stories WHERE filename LIKE ?\
                    OR author LIKE ? OR book_title LIKE ?", [\
            search_string,\
            search_string,\
            search_string,\
            ]).fetchall()
    return blob_list

def read_links(database_path, search_string='', output_max=20, blob='links'):
    """Вывод схожих рассказов таблицей."""
    database = sqlite3.connect(metadict_path(database_path))
    cursor = database.cursor()
    sql_list = get_blob(search_string, blob, cursor)
    # Испраивить. Не используется.
    #with open(metadict_path(TOKENS_DICT), "rb") as pickle_dict:
    #    tokens_dict = pickle.load(pickle_dict)
    for n,sql_tuple in enumerate(sql_list,1):
        print('# ----------------------------------------------------------------------------')
        print('# ', n, '/', len(sql_list), sql_tuple[0])
        print('# ----------------------------------------------------------------------------')
        cloud = pickle.loads(sql_tuple[1])
        cloud = dict_sort(cloud)
        n = 0
        for filename, value in cloud.items():
            book, author = get_bookdata(filename, cursor)
            # Вывод в процентах:
            value = round(value * 100, 5)
            if value > 0.1 and n < output_max:
                n = n + 1
                print ('{0:2} {1:10} | {3:30} | {2}'.format(n, round(value, 3),
                    book, author))
                #print(value, book_data[0],book_data[1])
            else:
                break

def read_blobs(database_path, search_string='', output_max=20, blob='tf_idf'):
    """Вывод ключевых слов таблицей."""
    database = sqlite3.connect(metadict_path(database_path))
    cursor = database.cursor()
    sql_list = get_blob(search_string, blob, cursor)
    # Исправить:
    # Берём сохранённый на диске словарь. Он огромный, пересоздавать медленно.
    # Да замени ты его парой запросов. Скорость вывода не так уж важна.
    with open(metadict_path(TOKENS_DICT), "rb") as pickle_dict:
        tokens_dict = pickle.load(pickle_dict)
    for n,sql_tuple in enumerate(sql_list,1):
        print('# ----------------------------------------------------------------------------')
        print('# ', n, '/', len(sql_list), sql_tuple[0])
        print('# ----------------------------------------------------------------------------')
        cloud = pickle.loads(sql_tuple[1])
        cloud = dict_sort(cloud)
        n = 0
        for word, value in cloud.items():
            book, author = get_bookdata(tokens_dict[word][1], cursor)
            if n < output_max:
                n = n + 1
                print ('{0:3} {1:10} | {2:30} | {3}'.format(n, round(value),
                    word, author))
            else:
                break

#-------------------------------------------------------------------------
# Тело программы:

if __name__ == '__main__':
    # Создаётся список аргументов скрипта:
    parser = create_parser()
    namespace = parser.parse_args()

    if namespace.database is not DATABASE_PATH:
        DATABASE_PATH = namespace.database

    if namespace.links is True:
        read_links(DATABASE_PATH, namespace.search_string, namespace.output_lines)
    else:
        read_blobs(DATABASE_PATH, namespace.search_string, namespace.output_lines)
