#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Скрипт извлекает глаголы из текстового файла с помощью pymorphy2

import os
import sys
import argparse
import pymorphy2

# Из местных скриптов:
from profiler_config import *
import wordfreq_morph

#-------------------------------------------------------------------------
# Аргументы командной строки:

def create_parser():
    """Список доступных параметров скрипта."""
    parser = argparse.ArgumentParser()
    parser.add_argument('file',
                        nargs='*',
                        help='Русскоязычный текстовый файл в UTF-8'
                        )
    return parser

#-------------------------------------------------------------------------
# Функции:

#-------------------------------------------------------------------------
# Тело программы:

if __name__ == '__main__':
    # Создаётся список аргументов скрипта:
    parser = create_parser()
    namespace = parser.parse_args()
    # Проверяем, существует ли указанный файл:
    file_patch = os.path.abspath(namespace.file[0])
    if namespace.file is not None and os.path.exists(file_patch):
        file = open(file_patch, "r")
        text = file.read()
        file.close()
    # Если нет, читаем стандартный ввод:
    else:
        text = sys.stdin.read()
    # Извлекаем из текста слова:
    words = wordfreq_morph.split_to_words(text)
    # Создаём частотный словарь:
    stats = wordfreq_morph.wordfreq_old(words)
    stats = wordfreq_morph.dict_sort(stats)
    # Нормализуем слова
    dict_verbs = {}
    morph = pymorphy2.MorphAnalyzer()
    for word,count in stats.items():
        # Слово анализируется, глаголы переносятся в словарь:
        word_parse = morph.parse(word)[0]
        #n_word = word_parse.normal_form
        if 'VERB' in word_parse.tag:
            dict_verbs[word] = count
    # Вывод данных
    for word, count in dict_verbs.items():
        print (count, word)
