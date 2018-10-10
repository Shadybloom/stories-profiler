#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Скрипт находит самые близкие к искомому тексты.
# На входе вывод wordfreq-ti-idf.py

import os
import sys
import collections
import argparse
import re
from math import log

#------------------------------------------------------------------------------
# Опции:

# Чувствительность скрипта
TF_IDF_SCORE_MIN = 3
TF_IDF_SCORE_MAX = 100

#-------------------------------------------------------------------------
# Функции:

def create_parser():
    """Список доступных параметров скрипта."""
    parser = argparse.ArgumentParser()
    parser.add_argument('file',
                        nargs='*',
                        help='Файл в wordfreq-morph.py (частота слово)'
                        )
    return parser

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

def find_path (file):
    """Возвращает путь к файлу, если он есть. Иначе выход."""
    if os.path.isfile(file):
        file_path = os.path.abspath(file)
    else:
        print('Неправильное имя файла.', file)
        print('Выход.')
        exit()
    return file_path

def dict_sort (stats):
    """Сортировка словаря по частоте и алфавиту"""
    stats_sort = collections.OrderedDict(sorted(stats.items(), key=lambda x: x[0], reverse=False))
    stats_list = collections.OrderedDict(sorted(stats_sort.items(), key=lambda x: x[1], reverse=True))
    return stats_list

#-------------------------------------------------------------------------
# Тело программы:

# Создаётся список аргументов скрипта:
parser = create_parser()
namespace = parser.parse_args()

# Проверяем, существует ли указанный файл:
file_patch = ' '.join(namespace.file)
wordlist = []
if namespace.file is not None and os.path.exists(file_patch):
    wordfreq_file = find_path(namespace.file[0])
    file = open(file_patch, "r")
    for line in file:
        wordlist.append(line)
    file.close()
# Если нет, читаем стандартный ввод:
else:
    wordfreq_file = None
    for line in sys.stdin:
        wordlist.append(line)

# Извлекаем из списка число IDF-TF, слово и фанфик, где оно чаще всего встречается.
dict_wordlist = {}
for line in wordlist:
    word_tf_idf = int(line.split()[0])
    word = str(line.split()[3])
    fic = str(line.split()[4])
    if word_tf_idf >= TF_IDF_SCORE_MIN and word_tf_idf <= TF_IDF_SCORE_MAX:
        dict_wordlist[word] = [word_tf_idf, fic]

# Сортируем словарь:
dict_wordlist = dict_sort(dict_wordlist)

dict_score = {}
for word in dict_wordlist:
    score = dict_wordlist[word][0]
    fic = dict_wordlist[word][1]
    if fic not in dict_score:
        dict_score[fic] = score
    else:
        dict_score[fic] = dict_score[fic] + score

# Сортируем словарь:
dict_score = dict_sort(dict_score)

for fic in dict_score:
    print(dict_score[fic], fic)
