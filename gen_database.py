#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Извлекаем текст, название и автора из fb2, fb2.zip и txt, переносим в базу данных.
# Создаём таблицы частоты слов (с нормализацией) и фраз под два-три слова (в чистом виде).

import re
import os
import sys
import argparse
import zipfile
import sqlite3
import pickle
import collections
from math import log
from lxml import etree
from itertools import groupby

# Функции из соседних скриптов:
import wordfreq_morph
from profiler_config import *

# Исправить. Таймер для тестов, не забудь убрать:
#import datetime

#-------------------------------------------------------------------------
# Функции:

def create_parser():
    """Список доступных параметров скрипта."""
    parser = argparse.ArgumentParser()
    parser.add_argument('file',
                        nargs='*',
                        help='Файлы в формате fb2'
                        )
    parser.add_argument('-R', '--regen',
                        action='store_true', default='False',
                        help='Перезаписывает основную таблицу в бд.'
                        )
    parser.add_argument('-D', '--database',
                        action='store', dest='database', type=str, default=DATABASE_PATH,
                        help='Путь к другой базе данных'
                        )
    return parser

def script_path (metadict_dir):
    """Возвращает абсолютный путь к каталогу скрипта."""
    # Получаем абсолютный путь к каталогу скрипта:
    script_path = os.path.dirname(os.path.abspath(__file__))
    # Добавляем к пути каталог словарей:
    script_path = script_path + '/' + metadict_dir
    return script_path

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

def pathfinder (pathlist):
    """Возвращает абсолютный путь к файлам в каталогах или к файлам в списке."""
    if type(pathlist) is str:
        pathlist = [ pathlist ]
    filelist = [ ]
    for file_path in pathlist:
        if os.path.isfile(file_path):
            filelist.append(file_path)
        if os.path.isdir(file_path):
            files = find_files(file_path)
            for file in files:
                filelist.append(file)
    return filelist

def correct_path (namespace_path, database_path=DATABASE_PATH, tokens_path=TOKENS_DICT):
    """Относительные пути к базе данных и рабочему словарю переводятся в абсолютные.
    
    Таким образом скрипт можно запускать из любого каталога.
    """
    if namespace_path is database_path:
        database_path = script_path(database_path)
        tokens_path = script_path(TOKENS_DICT)
    else:
        database_path = namespace_path
        tokens_path = os.path.splitext(namespace_path)[0] + '.pickle'
    return database_path,tokens_path

def extract_fb2_zip (file_path):
    """Извлекает текст (последний файл) из fb2.zip."""
    #if os.path.splitext(file)[1][1:] == 'zip':
    if zipfile.is_zipfile(file_path):
        zip_ref = zipfile.ZipFile(file_path, 'r')
        unzip_fb2 = zip_ref.open(zip_ref.namelist()[-1])
        zip_ref.close()
    return unzip_fb2

def extract_date_fb2 (tree):
    """Пытаемся извлечь дату создания рассказа.
    
    Используется объект etree:
    etree.parse(file_path)
    """
    try:
        if tree.find(".//{*}date").attrib and tree.find(".//{*}date").xpath(".//text()"):
            date = ''.join(tree.find(".//{*}date").xpath(".//text()"))
        elif tree.find(".//{*}date").attrib:
            date = tree.find(".//{*}date").attrib['value']
        elif tree.findall(".//{*}date")[-1].attrib:
            date = tree.findall(".//{*}date")[-1].attrib['value']
        else:
            date = ''.join(tree.find(".//{*}date").xpath(".//text()"))
        return date
    except Exception as error_output:
        print(error_output)
        return None

def clean_text (raw_text):
    """Чистим текст от пунктуации и повторяющихся слов."""
    cleant_text = re.findall(r"(\w+)", raw_text, re.UNICODE)
    # Удаляем повторяющиеся элементы в списке (сохраняя порядок):
    cleant_text = [el for el, _ in groupby(cleant_text)]
    cleant_text = ' '.join(cleant_text)
    #cleant_text = cleant_text.lower()
    return cleant_text

def cut_phrasedict (story_phrasefreq_dict, phrasefreq_min):
    """Фильтруем фразы по минимальному числу совпадений."""
    phrasefreq_dict_clean = { }
    for phrase,value in story_phrasefreq_dict.items():
        if value >= phrasefreq_min:
            phrasefreq_dict_clean[phrase] = value
    return phrasefreq_dict_clean

def dict_sort (stats):
    """Сортировка словаря по частоте и алфавиту"""
    stats_sort = collections.OrderedDict(sorted(stats.items(),
        key=lambda x: x[0], reverse=False))
    stats_list = collections.OrderedDict(sorted(stats_sort.items(),
        key=lambda x: x[1], reverse=True))
    return stats_list

def fb2_to_dict (file_path):
    """Создаёт словарь из книги в формате fb2.
    
    Название, автор, дата, аннотация и текст.
    Частотные словари слов и фраз.
    Счётчики слов и фраз.
    """
    # Из-за проблем с кодировкой часто бывают ошибки.
    # Надо бы найти годный декодер, а пока try.
    try:
        fb2_dict = {}
        tree = etree.parse(file_path)
        # Удаляем загрязняющий вывод id автора:
        author_id = tree.find(".//{*}author/{*}id")
        if author_id is not None:
            author_id.getparent().remove(author_id)
        fb2_dict['author'] = clean_text(' '.join(
            tree.find(".//{*}author").xpath(".//text()")))
        fb2_dict['book_title'] = clean_text(' '.join(
            tree.find(".//{*}book-title").xpath(".//text()")))
        fb2_dict['date_added'] = extract_date_fb2(tree)
        #print(fb2_dict['author'], fb2_dict['book_title'],fb2_dict['date_added'])
        fb2_dict['annotation'] = ' '.join(
                tree.find(".//{*}annotation").xpath(".//text()"))
        fb2_dict['body_text'] = ' '.join(
                tree.find(".//{*}body").xpath(".//text()"))
        fb2_dict['wordfreq'] = wordfreq_morph.run( \
                fb2_dict['body_text'], \
                morph_soft=MORPHY_SOFT, \
                morph_forced=MORPHY_FORCED)
        fb2_dict['phrasefreq'] = cut_phrasedict(wordfreq_morph.run( \
                fb2_dict['body_text'], \
                phrases=True, \
                phrases_tokenize=PHRASES_TOKENIZE),
                PHRASEFREQ_MIN)
        fb2_dict['wordcount'] = len(wordfreq_morph.split_to_words( \
                fb2_dict['body_text']))
        # Почини. Функцию сделай:
        fb2_dict['phrasecount'] = sum(fb2_dict['phrasefreq'].values())
        fb2_dict['wordfreq_count'] = len(fb2_dict['wordfreq'])
        fb2_dict['phrasefreq_count'] = len(fb2_dict['phrasefreq'])
        #print(fb2_dict['wordcount'], fb2_dict['wordfreq_count'],fb2_dict['phrasefreq_count'])
        return fb2_dict
    except Exception as error_output:
        print('Ошибка декодера:', error_output)
        return None

def txt_to_dict (text):
    """Создаёт словарь из куска текста.
    
    Частотные словари слов и фраз.
    Счётчики слов и фраз.
    """
    # Переносим данные в словарь:
    txt_dict = {}
    txt_dict['author'] = None
    txt_dict['book_title'] = None
    # Можно взять время создания файла:
    txt_dict['date_added'] = None
    txt_dict['annotation'] = None
    txt_dict['body_text'] = text
    txt_dict['wordfreq'] = wordfreq_morph.run( \
            text, \
            morph_soft=MORPHY_SOFT, \
            morph_forced=MORPHY_FORCED)
    txt_dict['phrasefreq'] = cut_phrasedict(wordfreq_morph.run( \
            text, \
            phrases=True, \
            phrases_tokenize=PHRASES_TOKENIZE),
            PHRASEFREQ_MIN)
    txt_dict['wordcount'] = len(wordfreq_morph.split_to_words(text))
    txt_dict['phrasecount'] = len(wordfreq_morph.split_to_phrases(text))
    txt_dict['wordfreq_count'] = len(txt_dict['wordfreq'])
    txt_dict['phrasefreq_count'] = len(txt_dict['phrasefreq'])
    #print(txt_dict['wordcount'], txt_dict['wordfreq_count'],txt_dict['phrasefreq_count'])
    return txt_dict

def create_stories_database (database_path):
    """База данных с названияим, авторами и текстами рассказов.
    
    Включает данные счётчиков и частотные списки слов/фраз.
    """
    database = sqlite3.connect(database_path)
    cursor = database.cursor()
    cursor.execute("""CREATE TABLE IF NOT EXISTS stories (
        id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
        filename TEXT NOT NULL,
        author TEXT DEFAULT NULL,
        book_title TEXT DEFAULT NULL,
        date_added TEXT DEFAULT NULL,
        annotation TEXT DEFAULT NULL,
        body_text TEXT DEFAULT NULL,
        wordcount INTEGER NOT NULL,
        phrasecount INTEGER NOT NULL,
        wordfreq_count INTEGER NOT NULL,
        phrasefreq_count INTEGER NOT NULL,
        wordfreq BLOB DEFAULT NULL,
        phrasefreq BLOB DEFAULT NULL,
        tf_idf BLOB DEFAULT NULL,
        links BLOB DEFAULT NULL
        )""")
    cursor.execute("""CREATE INDEX IF NOT EXISTS index_stories ON stories (
        id,
        filename,
        author,
        book_title,
        date_added,
        annotation,
        body_text,
        wordcount,
        phrasecount,
        wordfreq_count,
        phrasefreq_count,
        wordfreq,
        phrasefreq,
        tf_idf,
        links
        )""")
    database.close()
    print("[OK] CREATE:",database_path)

def create_words_table(cursor):
    """Таблица слов в базе данных.
    
    Включает слова, счётчики.
    И названия текстов, где чаще всего встречается это слово.
    """
    cursor.execute("""CREATE TABLE IF NOT EXISTS words (
        id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
        word TEXT NOT NULL,
        wordcount INTEGER NOT NULL,
        storycount INTEGER NOT NULL,
        word_percent INTEGER NOT NULL,
        top_filename TEXT DEFAULT NULL,
        top_story TEXT DEFAULT NULL,
        top_author TEXT DEFAULT NULL
        )""")
    cursor.execute("""CREATE INDEX IF NOT EXISTS index_words ON words (
        id,
        word,
        wordcount,
        storycount,
        word_percent,
        top_filename,
        top_story,
        top_author
        )""")

def create_phrases_table(cursor):
    """Таблица фраз в базе данных.
    
    Включает фразы, счётчики.
    И названия текстов, где чаще всего встречается эта фраза.
    """
    cursor.execute("""CREATE TABLE IF NOT EXISTS phrases (
        id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
        phrase TEXT NOT NULL,
        phrasecount INTEGER NOT NULL,
        storycount INTEGER NOT NULL,
        phrase_percent INTEGER NOT NULL,
        top_filename TEXT DEFAULT NULL,
        top_story TEXT DEFAULT NULL,
        top_author TEXT DEFAULT NULL
        )""")
    cursor.execute("""CREATE INDEX IF NOT EXISTS index_phrases ON phrases (
        id,
        phrase,
        phrasecount,
        storycount,
        phrase_percent,
        top_filename,
        top_story,
        top_author
        )""")

def test_table(database_path, table):
    """Проверяем наличие таблицы в БД."""
    sql_query = "SELECT name FROM sqlite_master WHERE type='table' AND name='{t}'".format(t=table)
    database = sqlite3.connect(database_path)
    cursor = database.cursor()
    tables_list = cursor.execute(sql_query).fetchall()
    if tables_list:
        return True

def stats_database(database_path):
    """Выводит статистику базы данных.
    
    Суммараное число слов (и усреднённое на рассказ)
    Число рассказов и авторов, число поисковых токенов.
    """
    database = sqlite3.connect(database_path)
    cursor = database.cursor()
    words_all = cursor.execute("SELECT SUM(wordcount) FROM stories").fetchone()[0]
    stories_all = cursor.execute("SELECT COUNT(id) FROM stories").fetchone()[0]
    authors_all = len(set(cursor.execute("SELECT author FROM stories").fetchall()))
    words = cursor.execute("SELECT count(id) FROM words").fetchone()[0]
    phrases = cursor.execute("SELECT count(id) FROM phrases").fetchone()[0]
    if None in (words_all, stories_all, authors_all, words, phrases):
        print('[ERROR] EMPTY DATABASE:', database_path)
    else:
        tokens_all = words + phrases
        wordcount_medial = round(words_all / stories_all)
        print("[READY]: WORDS {0:,d} (MID {1:,d}) KEYS {2:,d} STORIES {3:,d} AUTHORS {4:,d}"
                .format(words_all, wordcount_medial, tokens_all, stories_all, authors_all))

def purge_database(database_path):
    """Пересоздаём таблицы слов/фраз, обнуляем блобы tf_idf и links.

    Это приходится делать каждый раз с добавлением нового текста.
    Частичную переработку таблиц эта модель БД, увы, не поддерживает.
    """
    database = sqlite3.connect(database_path)
    cursor = database.cursor()
    # Дропаем таблицы и пересоздаём:
    cursor.execute("DROP TABLE IF EXISTS words")
    cursor.execute("DROP TABLE IF EXISTS phrases")
    create_words_table(cursor)
    create_phrases_table(cursor)
    # Убираем блобы, оставив сам обработанный текст:
    cursor.execute("UPDATE stories SET tf_idf=NULL, links=NULL")
    database.commit()
    database.close()

def book_to_database (database_path, file_path, fb2_dict):
    """Словарь книги переносится в базу данных.
    
    Для оптимизации используется pickle, бинарный формат питона.
    """
    # Проверка, сработал ли парсер:
    if not fb2_dict:
        return None
    # Подключается база данных:
    database = sqlite3.connect(database_path)
    cursor = database.cursor()
    # Элементы словаря в переменные:
    filename = str(os.path.basename(file_path))
    author = str(fb2_dict.get('author'))
    book_title = str(fb2_dict.get('book_title'))
    date_added = str(fb2_dict.get('date_added'))
    annotation = str(fb2_dict.get('annotation'))
    if SAVE_BOOK_TEXT is True:
        body_text = str(fb2_dict.get('body_text'))
    else:
        body_text = None
    wordcount = int(fb2_dict.get('wordcount'))
    phrasecount = int(fb2_dict.get('phrasecount'))
    wordfreq_count = int(fb2_dict.get('wordfreq_count'))
    phrasefreq_count = int(fb2_dict.get('phrasefreq_count'))
    # Запаковываем словари в блобы:
    wordfreq = pickle.dumps(fb2_dict.get('wordfreq'))
    phrasefreq = pickle.dumps(fb2_dict.get('phrasefreq'))
    # Без таблицы слов/фраз заполнить TF-IDF невозможно:
    tf_idf = None
    links = None
    #print(book_title,filename,date_added)
    # Переменные в базу данных:
    cursor.execute("INSERT INTO stories VALUES(NULL,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", [\
        filename,\
        author,\
        book_title,\
        date_added,\
        annotation,\
        body_text,\
        wordcount,\
        phrasecount,\
        wordfreq_count,\
        phrasefreq_count,\
        wordfreq,\
        phrasefreq,\
        tf_idf,\
        links,\
        ])
    database.commit()
    database.close()
    return wordcount

def filename_in_database (file_path, database_path):
    """Проверка, есть ли название в базе данных."""
    database = sqlite3.connect(database_path)
    filename = os.path.basename(file_path)
    cursor = database.cursor()
    filename_test = cursor.execute("SELECT filename FROM stories WHERE filename=?"\
            ,(filename,)).fetchall()
    return filename_test

def fill_words_dict(words_all_dict, story_wordfreq_dict, storytuple, count):
    """Общий словарь заполняется словами из словарей рассказов.

    Если слово уже есть, частота суммируется, а к числу совпадений добавляется единица.
    Если в новом рассказе слово встречается чаще, тогда этот рассказ ассоциируется со словом.
    Частота слова в процентах от текста рассказа.
    """
    filename, book_title, author = storytuple[0:3]
    wordcount = count
    for word, wordfreq in story_wordfreq_dict.items():
        # Если слова нет в общем списке, создаём:
        if word not in words_all_dict:
            word_percent = wordfreq / wordcount
            storycount = 1
            words_all_dict[word] = [wordfreq, storycount, word_percent,
                    filename, book_title, author]
        else:
            # Если слово есть в списке, пересчитываем:
            wordfreq_new = words_all_dict[word][0] + wordfreq
            storycount = words_all_dict[word][1] + 1
            word_percent = wordfreq / wordcount
            # Исправить.
            # Фигня получается. Диктат малых книг.
            # Если в новой книге чаще встречается слово, значит её в топ:
            if word_percent >= words_all_dict[word][2]:
                words_all_dict[word] = [wordfreq_new, storycount, word_percent,
                        filename, book_title, author]
            else:
                words_all_dict[word][0:2] = wordfreq_new, storycount
    return words_all_dict

def gen_words_table(database_path):
    """Создаём текстовый корпус. Самые распространённые слова в текстах.
    
    Эта функция -- пожиратель памяти, поскольку все ключи обрабатываются в RAM.
    """
    # Исправить.
    # Алгоритм шустрый, но жрёт память как свинья. Весь словарь в RAM.
    # Известно, как это исправить, но всю структуру бд придётся переписать.
    words_all_dict = {}
    phrases_all_dict = {}
    database = sqlite3.connect(database_path)
    cursor = database.cursor()
    stories_list = cursor.execute("SELECT id, filename FROM stories").fetchall()
    for nametuple in stories_list:
        story_id, filename = nametuple
        sql_query = "SELECT filename, book_title, author,\
                wordcount, phrasecount, wordfreq, phrasefreq\
                FROM stories WHERE id={0}".format(story_id)
        storytuple = cursor.execute(sql_query).fetchone()
        wordcount = storytuple[3]
        phrasecount = storytuple[4]
        story_wordfreq_dict = pickle.loads(storytuple[5])
        story_phrasefreq_dict = pickle.loads(storytuple[6])
        # Исправить.
        # Данные можно записывать после каждой обработки словаря.
        # Да бесполезно, всё равно словарь в памяти приходится держать.
        # По очереди перебираем слова из списка рассказа, обновляем объединённый словарь:
        fill_words_dict(words_all_dict, story_wordfreq_dict, storytuple, wordcount)
        fill_words_dict(phrases_all_dict, story_phrasefreq_dict, storytuple, phrasecount)
        # Миллионы, миллионы ключей!
        keys_test = len(words_all_dict) + len(phrases_all_dict)
        ram_test = (int(sys.getsizeof(words_all_dict))\
                + int(sys.getsizeof(phrases_all_dict))) /1024 /1024
        # Бесполезное украшательство такое бесполезное (зато проблемный словарь на виду):
        print('{0} / {1} {2:60} | {3:10,d} KEYS: {4:4,d} Mb'.format(
            story_id, len(stories_list), filename, keys_test, round(ram_test)))
    for word,data in words_all_dict.items():
        # Можно резко сократить размер словаря, если вместо имён/названий вставлять id рассказа.
        # Нифига подобного. Словари -- умные штуки, одну запись по 100500 раз не дублируют.
        wordcount, storycount, word_percent, top_filename, top_story, top_author = data
        cursor.execute("INSERT INTO words VALUES(NULL,?,?,?,?,?,?,?)", [\
            word,\
            wordcount,\
            storycount,\
            word_percent,\
            top_filename,\
            top_story,\
            top_author,\
        ])
    for phrase,data in phrases_all_dict.items():
        phrasecount, storycount, phrase_percent, top_filename, top_story, top_author = data
        cursor.execute("INSERT INTO phrases VALUES(NULL,?,?,?,?,?,?,?)", [\
            phrase,\
            phrasecount,\
            storycount,\
            phrase_percent,\
            top_filename,\
            top_story,\
            top_author,\
        ])
    database.commit()
    database.close()
    print("[OK] CREATE {0:,d} KEYS: {1}".format(keys_test, database_path))

def gen_tokens_dict(database_path):
    """Создаёт словарь соответствий: слово -- число текстов с ним, ключевой текст"""
    database = sqlite3.connect(database_path)
    cursor = database.cursor()
    tokens_dict = {}
    words_list = cursor.execute(
            "SELECT word, storycount, top_filename FROM words").fetchall()
    phrases_list = cursor.execute(
            "SELECT phrase, storycount, top_filename FROM phrases").fetchall()
    # Сначала фразы, затем слова:
    for i in phrases_list:
        tokens_dict[i[0]] = i[1:3]
    # Малозначимые значения перезаписываются:
    for i in words_list:
        tokens_dict[i[0]] = i[1:3]
    return tokens_dict

def create_tokens_dict(database_path=DATABASE_PATH, tokens_path=TOKENS_DICT):
    """Сохраняем словарь рядом с базой данных, потому что он весит 100+ Mb."""
    tokens_dict = gen_tokens_dict(database_path)
    if tokens_path is TOKENS_DICT:
        tokens_path = script_path(TOKENS_DICT)
    with open(tokens_path, "wb") as output_file:
        pickle.dump(tokens_dict, output_file)
        output_file.close
        print("[OK] CREATE",tokens_path)
    return tokens_dict

def load_tokens_dict(database_path=DATABASE_PATH, file_path=TOKENS_DICT):
    """Загружаем словарь, или создаём, если вдруг потерялся."""
    # Сначала проверяем путь на соответствие стандартному:
    if file_path is TOKENS_DICT:
        file_path = script_path(TOKENS_DICT)
    # А затем обрабатываем файл:
    if os.path.isfile(file_path):
        with open(file_path, "rb") as pickle_dict:
            tokens_dict = pickle.load(pickle_dict)
        pickle_dict.closed
    # Если словаря нет в файле, генерируем временный:
    else:
        tokens_dict = gen_tokens_dict(database_path)
    return tokens_dict

def tf_idf(wordfreq_dict, tokens_dict):
    """Функция вычисляет рейтинг TF-IDF для каждого слова в словаре.

    TF-IDF вычисляется для каждого слова по очень простой формуле TF x IDF, где:
    TF (Term Frequency) -- частота слова в тексте, количество повторений.
    IDF (Inverse Document Frequency) -- величина, обратная количеству текстов,
    содержащих в себе это слово.

    Например:
    tf_idf = tf x log(N/n)
    Где:
    tf -- частота слова в тексте
    N -- общее кол-во текстов в выборке,
    n -- кол-во текстов, в которых есть это слово.
    """
    score_dict = {}
    # Определяем N по словарю:
    stories_list = [el[1] for el in tokens_dict.values()]
    storycount_all = len(set(stories_list))
    # Перебор слов, вычисление рейтинга:
    for word, wordfreq in wordfreq_dict.items():
        if word in tokens_dict:
            storycount = tokens_dict[word][0]
        else:
            storycount = 1
        # Основная формула скрипта:
        word_score = wordfreq * log(storycount_all / storycount)
        score_dict[word] = word_score
    return score_dict

def gen_wordfreq_idf(database_path, tokens_dict=TOKENS_DICT):
    """Функция вычисляет параметры TF-IDF для слов каждого текста в базе данных."""
    database = sqlite3.connect(database_path)
    cursor = database.cursor()
    stories_list = cursor.execute(
            "SELECT id, filename FROM stories WHERE tf_idf IS NULL"
            ).fetchall()
    if len(stories_list) == 0:
        return
    storycount_all = cursor.execute("SELECT count(id) FROM stories").fetchone()[0]
    tokens_dict = load_tokens_dict(database_path, tokens_path)
    # По очереди перебираем рассказы и создаём словари TF-IDF
    tf_counter = 0
    for nametuple in stories_list:
        story_id, filename = nametuple
        # Берём кортеж из базы данных:
        storytuple = cursor.execute(
                "SELECT wordfreq, phrasefreq FROM stories WHERE id=?"\
                ,(story_id,)).fetchone()
        story_wordfreq_dict = pickle.loads(storytuple[0])
        story_phrasefreq_dict = pickle.loads(storytuple[1])
        # Перебираем слова в тексте. Если находим, вычисляем TF-IDF:
        wordscore_dict = tf_idf(story_wordfreq_dict, tokens_dict)
        phrasescore_dict = tf_idf(story_phrasefreq_dict, tokens_dict)
        # Обновляем словарь фраз словарём слов:
        phrasescore_dict.update(wordscore_dict)
        tf_counter += len(phrasescore_dict)
        score_dict = phrasescore_dict
        score_dict = pickle.dumps(score_dict)
        cursor.execute("UPDATE stories SET tf_idf=? WHERE filename=?", [\
            score_dict,\
            filename,\
            ])
        database.commit()
        print('{0} / {1} {2:60} | {3:10,d} TF-IDF'.format(
            story_id, storycount_all, filename, tf_counter))
    database.close()
    print("[OK] CREATE {0:,d} TF-IDF: {1}".format(tf_counter, database_path))

def create_linkscloud(local_dict, tokens_dict, score_min=SCORE_MIN, score_max=SCORE_MAX):
    dict_links = {}
    scorecount = sum(local_dict.values())
    for token, score in local_dict.items():
        # Чувствительность настраивается по абсолютным показателям:
        if score >= score_min and score < score_max:
            # А резльтаты, для удобства, в относительных:
            percent_score = score / scorecount
            if token in tokens_dict:
                #print(token, tokens_dict[token])
                # Находим название и делаем ключом словаря:
                top_filename = tokens_dict[token][1]
                if top_filename not in dict_links:
                    dict_links[top_filename] = percent_score
                else:
                    dict_links[top_filename] += percent_score
    return dict_links

def gen_links(database_path, tokens_dict=TOKENS_DICT):
    """Функция вычисляет граф связей для всех текстов."""
    database = sqlite3.connect(database_path)
    cursor = database.cursor()
    stories_list = cursor.execute(
            "SELECT id, filename FROM stories WHERE links IS NULL").fetchall()
    if len(stories_list) == 0:
        return
    storycount_all = cursor.execute("SELECT count(id) FROM stories").fetchone()[0]
    tokens_dict = load_tokens_dict(database_path, tokens_path)
    # По очереди перебираем рассказы и создаём словари TF-IDF
    links_counter = 0
    for nametuple in stories_list:
        story_id, filename = nametuple
        tokens_tuple = cursor.execute("SELECT tf_idf FROM stories WHERE id=?"\
                ,(story_id,)).fetchone()
        local_dict = pickle.loads(tokens_tuple[0])
        dict_links = create_linkscloud(local_dict, tokens_dict)
        links_counter += len(dict_links)
        dict_links = pickle.dumps(dict_links)
        cursor.execute("UPDATE stories SET links=? WHERE filename=?", [\
            dict_links,\
            filename,\
            ])
        database.commit()
        print('{0} / {1} {2:60} | {3:10,d} LINKS'.format(
            story_id, storycount_all, filename, links_counter))
    database.close()
    print("[OK] CREATE {0:,d} LINKS: {1}".format(links_counter, database_path))

def consume_files(filelist, database_path):
    """Определяем тип файла, конвертируем и переносим в базу данных.

    Скрипт умеет распаковывать fb2.zip, парсит fiction_book и читает txt.
    """
    texts_count = 0
    words_count = 0
    words_consume = 0
    for n,file_path in enumerate(filelist,1):
        # Проверяем по имени файла, есть ли такой в базе данных:
        if not filename_in_database(file_path, database_path):
            # fb2.zip распаковываем, fb2 парсим, текст исследуем:
            try:
                if zipfile.is_zipfile(file_path):
                    fb2 = extract_fb2_zip(file_path)
                    # Переносим книги в БД, заодно считаем слова:
                    words_consume = book_to_database(
                            database_path, file_path, fb2_to_dict(fb2))
                elif os.path.splitext(file_path)[1][1:] == 'fb2':
                    fb2 = file_path
                    words_consume = book_to_database(
                            database_path, file_path, fb2_to_dict(fb2))
                else:
                    file = open(file_path, "r")
                    text = file.read()
                    file.close()
                    words_consume = book_to_database(
                            database_path, file_path, txt_to_dict(text))
                texts_count += 1
            except Exception as error_output:
                print(error_output)
            if words_consume is None:
                words_consume = 0
            words_count += words_consume
            print('{0} / {1} {2:60} | {3:10,d} WORDS'.format(
                n, len(filelist), file_path, words_consume))
    print("[OK] GET {0:,d} WORDS: {1}".format(words_count, database_path))
    return texts_count

#-------------------------------------------------------------------------
# Тело программы:

if __name__ == '__main__':
    # Создаётся список аргументов скрипта:
    parser = create_parser()
    namespace = parser.parse_args()
    # Создаём список файлов:
    if namespace.file:
        filelist = (pathfinder(namespace.file))
    else:
        # Больше проблем создаёт, чем пользы:
        #filelist = (pathfinder(script_path(BOOKS_DIR)))
        filelist = [ ]
    # Уточняем пути к базе данных и основному словарю:
    database_path, tokens_path = correct_path(namespace.database)
    # Проверяем базу данных:
    if os.path.exists(database_path) is not True:
        create_stories_database(database_path)
        purge_database(database_path)
    elif test_table(database_path, 'stories') is not True:
        purge_database(database_path)
    # Обрабатываем книги, заргужаем в базу данных:
    if filelist:
        print("[CONSUME]: {0}".format(namespace.file))
        texts_count = consume_files(filelist, database_path)
    else:
        texts_count = 0
    # Создаём таблицу ключевых слов/фраз, а затем словари TF-IDF и граф связей:
    if texts_count > 0 or namespace.regen is True:
        print("[REGEN]: {0}".format(database_path))
        purge_database(database_path)
        gen_words_table(database_path)
        create_tokens_dict(database_path, tokens_path)
        gen_wordfreq_idf(database_path, tokens_path)
        gen_links(database_path, tokens_path)
        stats_database(database_path)
    # Если таблицы неполные (из-за прерывания), пополняем:
    else:
        print("[RESUME]: {0}".format(database_path))
        if os.path.exists(tokens_path) is not True:
            create_tokens_dict(database_path, tokens_path)
        gen_wordfreq_idf(database_path, tokens_path)
        gen_links(database_path, tokens_path)
        stats_database(database_path)
