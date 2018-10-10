#!/usr/bin/env python
# -*- coding: utf-8 -*-

# На входе вывод wordfreq-morph.py (лучше с нормализацией, с ключом -m)

# TF-IDF вычисляется для каждого слова по очень простой формуле TF x IDF, где:
# TF (Term Frequency) — частота слова в тексте, я взял просто количество повторений.
# IDF (Inverse Document Frequency) — величина, обратная количеству текстов, содержащих в себе это слово.
# Я взял log(N/n), где N — общее кол-во текстов в выборке, n — кол-во текстов, в которых есть это слово.


# Причеши код, по функциям раскидай, стыдоба же!


import os
import sys
import collections
import argparse
import re
from math import log

#------------------------------------------------------------------------------
# Опции:

# Каталог словарей созданных wordfreq-morph.py
WORDS_DIR = 'words'
#WORDFREQ_ALL = 'wordfreq-all.list'
WORDFREQ_ALL = 'wordfreq-50k.list'

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

wordfreq_all = find_path(WORDFREQ_ALL)

# Создаём общий словарь:
dict_wordfreq_all = {}
with open(wordfreq_all) as file:
    for line in file:
        number = int(line.split()[0])
        texts = int(line.split()[1])
        word = str(line.split()[2])
        fic = str(line.split()[3])
        dict_wordfreq_all[word] = [number, texts, fic]
file.close()

# Создаём словарь исследуемого текста:
dict_wordlist = {}
for line in wordlist:
    number = int(line.split()[0])
    word = str(line.split()[1])
    if word in dict_wordfreq_all:
        number_all = dict_wordfreq_all[word][0]
        texts = dict_wordfreq_all[word][1] + 1
        fic = dict_wordfreq_all[word][2]
    else:
        number_all = number
        texts = 1
        fic = ''.join(re.findall('[^/]+$', str(wordfreq_file)))
    texts_all = len(find_files(metadict_path(WORDS_DIR)))
    word_idf = log(texts_all/texts)
    # Число совпадение x редкость слова = значимость слова
    # Числа с плавающей запятой превращаются в натуральные
    word_tf_idf = number * int((word_idf * 1000) / 1000)
    dict_wordlist[word] = [word_tf_idf, number, texts, fic]

# Сортируем словарь:
dict_wordlist = dict_sort(dict_wordlist)

for word in dict_wordlist:
    list = dict_wordlist[word]
    print(list[0], list[1], list[2], word, list[3])
