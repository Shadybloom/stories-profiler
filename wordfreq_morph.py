#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Скрипт извлекает слова из текстового файла и сортирует их по частоте.
# С помощью модуля pymorphy2 можно привести слова к начальной форме (единственное число, именительный падеж).

# Нужен pymorphy2 и русскоязычный словарь для него!
# pip install --user pymorphy2

# Примеры:
# ./wordfreq-morph.py ./text-file.txt | less
# xclip -o | ./wordfreq-morph.py -m

# Проверялся на интерпретаторе:
# Python 3.6.1 on linux

import sys
import sqlite3
import os
import re
import argparse
import collections
import pymorphy2

#------------------------------------------------------------------------------
# Опции:

# Проверочный морфологический словарь (в каталоге скрипта):
NORMAL_DICT_PATH = 'dict.opencorpora-sing-nom.txt'
NORMAL_DICT_DIR = 'word-length-dicts'
database_name = '/database/opencorpora-sing-nom.sqlite'

#-------------------------------------------------------------------------
# Аргументы командной строки:

def create_parser():
    """Список доступных параметров скрипта."""
    parser = argparse.ArgumentParser()
    parser.add_argument('file',
                        nargs='*',
                        help='Русскоязычный текстовый файл в UTF-8'
                        )
    parser.add_argument('-m', '--morph_soft',
                        action='store_true', default='False',
                        help='Преобразование слов в начальную форму'
                        )
    parser.add_argument('-M', '--morph_forced',
                        action='store_true', default='False',
                        help='Слова в нормальную форму, в том числе неологизмы'
                        )
    parser.add_argument('-p', '--phrase',
                        action='store_true', default='False',
                        help='Частота фраз (словосочетаний, разделённых пунктуацией)'
                        )
    return parser

#-------------------------------------------------------------------------
# Функции:

def metadict_path (metadict_dir):
    """Возвращает абсолютный путь к каталогу словарей."""
    # Получаем абсолютный путь к каталогу скрипта:
    script_path = os.path.dirname(os.path.abspath(__file__))
    # Добавляем к пути каталог словарей:
    metadict_path = script_path + '/' + metadict_dir
    return metadict_path

def find_files (directory):
    """Возвращает список путей ко всем файлам каталога, включая подкаталоги."""
    path_f = []
    for d, dirs, files in os.walk(directory):
        for f in files:
                # Формирование адреса:
                path = os.path.join(d,f)
                # Добавление адреса в список:
                path_f.append(path)
    return path_f

def split_to_words (text):
    """Создаёт из текста список слов в нижнем регистре."""
    # Переводим текст в нижний регистр:
    text = str(text.lower())
    # Регексп вытаскивает из текста слова:
    words = re.findall(r"(\w+)", text, re.UNICODE)
    # Восстанавливаются ссылки:
    #urls = re.findall('http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', text)
    #words = words + urls
    return words

def split_to_phrases (text):
    """Делит текст на фразы, разделённые знаками препинания."""
    # Делим текст на фразы (разделённые знаками препинания):
    phrases_raw = re.split('\W+ |\n', text)
    phrases_clean = [ ]
    for element in phrases_raw:
        # Переводим в нижний регистр, чистим от пунктуации:
        element = str(element.lower())
        phrases_clean.append(' '.join(re.findall(r"(\w+)", element, re.UNICODE)))
    return phrases_clean

def wordfreq_old (words):
    """Создаёт словарь с частотой слов"""
    stats = {}
    # Слово -- ключ словаря, значение, это его частота:
    for word in words:
        stats[word] = stats.get(word, 0) + 1
    return stats

def word_search_opencorpora (word,cursor):
    """Проверяет, есть ли слово в базе данных"""
    # Номер таблицы, это длина слова:
    word_length = len(word)
    tables = cursor.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()
    if word_length > len(tables):
        word_length = 32
    table_name = 'opencorpora' + str(word_length)
    result = cursor.execute("SELECT words FROM "+table_name+" WHERE words=?",(word,)).fetchall()
    if result:
        return True
    else:
        return False

def wordfreq_morph (words, cursor, morph_forced=False):
    """Создаёт словарь с частотой слов (в начальной форме)"""
    # Морфологический анализатор:
    stats = {}
    n_stats = {}
    # Сначала создаётся словарь с частотой слов в тексте:
    stats = collections.Counter(words)
    # Далее словарь передаётся морфологическому анализатору:
    morph = pymorphy2.MorphAnalyzer()
    for word in stats:
        # Слово нормализуется:
        n_word = morph.parse(word)[0].normal_form
        # Неологизмы остаются без изменений:
        if morph_forced is not True:
            if word_search_opencorpora(n_word,cursor) is not True:
                n_word = word
        # Создаётся новый ключ, или прибавляется значение к существующему:
        if n_word not in n_stats:
            n_stats[n_word] = stats[word]
        else:
            n_stats[n_word] = n_stats[n_word] + stats[word]
    return n_stats

def dict_sort (stats):
    """Сортировка словаря по частоте и алфавиту"""
    stats_sort = collections.OrderedDict(sorted(stats.items(), key=lambda x: x[0], reverse=False))
    stats_list = collections.OrderedDict(sorted(stats_sort.items(), key=lambda x: x[1], reverse=True))
    return stats_list

def run (text, morph_soft=False, morph_forced=False, phrase=False):
    """Создаём словарь с частотой слов/фраз."""
    # Извлекаем из текста слова:
    words = split_to_words(text)
    # Подключение к базе данных:
    database = sqlite3.connect(metadict_path(database_name))
    cursor = database.cursor()
    # Если указано преобразование слов:
    if morph_soft is True and phrase is not True:
        dict_wordfreq = wordfreq_morph(words, cursor, morph_forced)
    elif morph_soft is not True and phrase is not True:
        dict_wordfreq = wordfreq_old(words)
    elif phrase is True:
        dict_wordfreq = wordfreq_old(split_to_phrases(text))
    else:
        print('nya',morph_soft,phrase)
        dict_wordfreq = wordfreq_old(words)
    # Отключаемся от базы данных:
    database.close()
    return dict_wordfreq

#-------------------------------------------------------------------------
# Тело программы:

if __name__ == '__main__':
    # Создаётся список аргументов скрипта:
    parser = create_parser()
    namespace = parser.parse_args()
    # Проверяем, существует ли указанный файл:
    file_patch = ' '.join(namespace.file)
    if namespace.file is not None and os.path.exists(file_patch):
        file = open(file_patch, "r")
        text = file.read()
        file.close()
    # Если нет, читаем стандартный ввод:
    else:
        text = sys.stdin.read()
    # Исполняется главная функция, создаётся словарь:
    dict_wordfreq = run(text, namespace.morph_soft, namespace.morph_forced, namespace.phrase)
    # Сортировка словаря:
    dict_wordfreq = dict_sort(dict_wordfreq)
    # Вывод словаря:
    for word, count in dict_wordfreq.items():
        print (count, word)
