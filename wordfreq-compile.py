#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Скрипт объединяет частотные словари wordfreq-morph.py в единый словарь,
# Подсчитывает суммарное количество слов и вхождений слова в рассказы.

import os
import collections
import re

#------------------------------------------------------------------------------
# Опции:

# Каталог словарей созданных wordfreq-morph.py
#WORDS_DIR = 'words'
WORDS_DIR = 'words50k'

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

def dict_sort (stats):
    """Сортировка словаря по частоте и алфавиту"""
    stats_sort = collections.OrderedDict(sorted(stats.items(), key=lambda x: x[0], reverse=False))
    stats_list = collections.OrderedDict(sorted(stats_sort.items(), key=lambda x: x[1], reverse=True))
    return stats_list

#-------------------------------------------------------------------------
# Тело программы:

dict_words = {}
for file_patch in (find_files(metadict_path(WORDS_DIR))):
    with open(file_patch) as file:
        #Ищем строку в файле
        for line in file:
            number = int(line.split()[0])
            word = str(line.split()[1])
            filename = ''.join(re.findall('[^/]+$', str(file_patch)))
            if word not in dict_words:
                # Если слова нет в словаре, создаём.
                number_count = number
                dict_words[word] = [number, 1, filename, number_count]
            else:
                # Если есть, суммирум и добавляем единичку к числу совпадений.
                dict_words[word][0] = dict_words[word][0] + number
                dict_words[word][1] = dict_words[word][1] + 1
                # Вывод имени фанфика с наибольшим числом совпадений слова:
                if number > dict_words[word][3]:
                    number_count = number
                    dict_words[word][2] = filename
                    dict_words[word][3] = number_count

# Сортируем словарь:
dict_words = dict_sort(dict_words)

# Вывод данных:
for word in dict_words:
    print(dict_words[word][0], dict_words[word][1], word, dict_words[word][2])
