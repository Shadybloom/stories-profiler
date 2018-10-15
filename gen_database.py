#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Извлекаем текст, название и автора из fb2, fb2.zip и txt, переносим в базу данных.
# Создаём таблицы частоты слов (с нормализацией) и фраз (разделённых знаками препинания).

import os
import re
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

#-------------------------------------------------------------------------
# Функции:

def create_parser():
    """Список доступных параметров скрипта."""
    parser = argparse.ArgumentParser()
    parser.add_argument('file',
                        nargs='*',
                        help='Файлы в формате fb2'
                        )
    parser.add_argument('-s', '--search',
                        action='store', dest='search_string', type=str, nargs='*', default='',
                        help='Поиск в базе данных'
                        )
    parser.add_argument('-S', '--score',
                        action='store', dest='output_max', type=int, default=20,
                        help='Число строк в выводе.'
                        )
    parser.add_argument('-l', '--links',
                        action='store_true', default='False',
                        help='Вывод таблицы схожих текстов'
                        )
    parser.add_argument('-o', '--output',
                        action='store_true', default='False',
                        help='Вывод таблицы ключевых слов'
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
    #cleant_text = '_'.join(cleant_text)
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
    stats_sort = collections.OrderedDict(sorted(stats.items(), key=lambda x: x[0], reverse=False))
    stats_list = collections.OrderedDict(sorted(stats_sort.items(), key=lambda x: x[1], reverse=True))
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
        fb2_dict['author'] = clean_text(' '.join(tree.find(".//{*}author").xpath(".//text()")))
        fb2_dict['book_title'] = clean_text(' '.join(tree.find(".//{*}book-title").xpath(".//text()")))
        fb2_dict['date_added'] = extract_date_fb2(tree)
        #print(fb2_dict['author'], fb2_dict['book_title'],fb2_dict['date_added'])
        fb2_dict['annotation'] = ' '.join(tree.find(".//{*}annotation").xpath(".//text()"))
        fb2_dict['body_text'] = ' '.join(tree.find(".//{*}body").xpath(".//text()"))
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
    database = sqlite3.connect(metadict_path(database_path))
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
    print("[OK] CREATE",database_path)

def create_words_table(database_path):
    """Таблица слов в базе данных.
    
    Включает слова, счётчики.
    И названия текстов, где чаще всего встречается это слово.
    """
    database = sqlite3.connect(metadict_path(database_path))
    cursor = database.cursor()
    cursor.execute(
            "DROP TABLE IF EXISTS words"
            )
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
    database.close()

def create_phrases_table(database_path):
    """Таблица фраз в базе данных.
    
    Включает фразы, счётчики.
    И названия текстов, где чаще всего встречается эта фраза.
    """
    database = sqlite3.connect(metadict_path(database_path))
    cursor = database.cursor()
    cursor.execute(
            "DROP TABLE IF EXISTS phrases"
            )
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
    database.close()

def book_to_database (database_path, file_path, fb2_dict):
    """Словарь книги переносится в базу данных.
    
    Для оптимизации используется pickle, бинарный формат питона.
    """
    # Создаётся база данных, если её нет:
    if os.path.exists(metadict_path(database_path)) is not True:
        create_stories_database(database_path)
    # Проверка, сработал ли парсер:
    if not fb2_dict:
        return None
    # Подключается база данных:
    database = sqlite3.connect(metadict_path(database_path))
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

def filename_in_database (file_path, database_path):
    """Проверка, есть ли название в базе данных."""
    database = sqlite3.connect(metadict_path(database_path))
    filename = os.path.basename(file_path)
    cursor = database.cursor()
    filename_test = cursor.execute("SELECT filename FROM stories WHERE filename=?"\
            ,(filename,)).fetchall()
    return filename_test

def fill_words_dict(words_all_dict, story_wordfreq_dict, story_tuple, count):
    """Общий словарь заполняется словами из словарей рассказов.

    Если слово уже есть, частота суммируется, а к числу совпадений добавляется единица.
    Если в новом рассказе слово встречается чаще, тогда этот рассказ ассоциируется со словом.
    Частота слова в процентах от текста рассказа.
    """
    filename, book_title, author = story_tuple[0:3]
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
    """Создаём текстовый корпус. Самые распространённые слова в текстах."""
    # Алгоритм шустрый, но жрёт память как свинья. Весь словарь в RAM.
    # Поразмысли, может, лучше в первый цикл засунуть не рассказы, а слова.
    # И записывать значения в таблицу после обработки каждого слова.
    # Но тогда получается слишком много обращений к бд.
    words_all_dict = {}
    phrases_all_dict = {}
    database = sqlite3.connect(metadict_path(database_path))
    cursor = database.cursor()
    stories_list = cursor.execute(
            "SELECT filename,book_title,author,\
            wordcount,phrasecount,wordfreq,phrasefreq FROM stories"
            ).fetchall()
    # Исправить.
    # Вовсе не обязательно сносить таблицы, можно ведь обновить!
    create_words_table(database_path)
    create_phrases_table(database_path)
    print('Создан и заполняется текстовый корпус:')
    for n,story_tuple in enumerate(stories_list,1):
        print(n, '/', len(stories_list), story_tuple[0])
        # Берём переменные из базы данных:
        wordcount = story_tuple[3]
        phrasecount = story_tuple[4]
        story_wordfreq_dict = pickle.loads(story_tuple[5])
        story_phrasefreq_dict = pickle.loads(story_tuple[6])
        # Исправить.
        # Данные можно записывать после каждой обработки словаря.
        # Да бесполезно, всё равно словарь в памяти приходится держать.
        # По очереди перебираем слова из списка рассказа, обновляем объединённый словарь:
        fill_words_dict(words_all_dict, story_wordfreq_dict, story_tuple, wordcount)
        fill_words_dict(phrases_all_dict, story_phrasefreq_dict, story_tuple, phrasecount)
    for word,data in words_all_dict.items():
        #print(data,word)
        cursor.execute("INSERT INTO words VALUES(NULL,?,?,?,?,?,?,?)", [\
            word,\
            data[0],\
            data[1],\
            data[2],\
            data[3],\
            data[4],\
            data[5],\
        ])
    for phrase,data in phrases_all_dict.items():
        #print(data,phrase)
        cursor.execute("INSERT INTO phrases VALUES(NULL,?,?,?,?,?,?,?)", [\
            phrase,\
            data[0],\
            data[1],\
            data[2],\
            data[3],\
            data[4],\
            data[5],\
        ])
    database.commit()
    database.close()

def storycount(database_path):
    """Создаёт словарь соотвествий слово/фраза -- число докуметнов, где искомое есть."""
    database = sqlite3.connect(metadict_path(database_path))
    cursor = database.cursor()
    storycount_dict = {}
    words_list = cursor.execute("SELECT word,storycount FROM words").fetchall()
    phrases_list = cursor.execute("SELECT phrase,storycount FROM phrases").fetchall()
    # Сначала фразы, потом слова:
    for phrase in phrases_list:
        storycount_dict[phrase[0]] = phrase[1]
    for word in words_list:
        storycount_dict[word[0]] = word[1]
    return storycount_dict

def gen_authors_dict(database_path):
    """Создаёт словарь соответствий слово/фраза -- файл, автор, история."""
    database = sqlite3.connect(metadict_path(database_path))
    cursor = database.cursor()
    authors_dict = {}
    words_list = cursor.execute("SELECT word,top_filename,top_story,top_author FROM words").fetchall()
    phrases_list = cursor.execute("SELECT phrase,top_filename,top_story,top_author FROM phrases").fetchall()
    # Сначала фразы, потом слова:
    for phrase in phrases_list:
        authors_dict[phrase[0]] = phrase[1:5]
    for word in words_list:
        authors_dict[word[0]] = word[1:5]
    return authors_dict

def gen_wordfreq_idf(database_path):
    """Функция вычисляет параметры TF-IDF для слов каждого текста в базе данных.

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
    database = sqlite3.connect(metadict_path(database_path))
    cursor = database.cursor()
    storycount_dict = storycount(database_path)
    storycount_all = len(cursor.execute("SELECT filename FROM stories").fetchall())
    filenames_list = cursor.execute(
            "SELECT filename,wordfreq,phrasefreq FROM stories"
            ).fetchall()
    print('Создаются частотные словари TF-IDF:')
    # По очереди перебираем рассказы и создаём словари TF-IDF
    for n,story_tuple in enumerate(filenames_list,1):
        print(n, '/', len(filenames_list), story_tuple[0])
        score_dict = {}
        filename = story_tuple[0]
        story_wordfreq_dict = pickle.loads(story_tuple[1])
        story_phrasefreq_dict = pickle.loads(story_tuple[2])
        # Перебираем слова в тексте. Если находим, вычисляем TF-IDF:
        for word,wordfreq in story_wordfreq_dict.items():
            word_score = wordfreq * log(storycount_all/storycount_dict[word])
            if word in storycount_dict:
                score_dict[word] = word_score
        for phrase,phrasefreq in story_phrasefreq_dict.items():
            phrase_score = phrasefreq * log(storycount_all/storycount_dict[phrase])
            if phrase in storycount_dict:
                score_dict[phrase] = phrase_score
        # Тесты:
        #score_dict = dict_sort(score_dict)
        #for el, value in score_dict.items():
        #    if value > 5:
        #        print(value, el)
        score_dict = pickle.dumps(score_dict)
        cursor.execute("UPDATE stories SET tf_idf=? WHERE filename=?", [\
            score_dict,\
            filename,\
            ])
        database.commit()
    database.close()

def words_to_dict(database_path):
    """Создаёт словарь соответствий: слово/фраза -- рассказ."""
    words_dict = { }
    database = sqlite3.connect(metadict_path(database_path))
    cursor = database.cursor()
    words_list = cursor.execute(
            "SELECT word,top_filename FROM words"
            ).fetchall()
    phrases_list = cursor.execute(
            "SELECT phrase,top_filename FROM phrases"
            ).fetchall()
    words_list.extend(phrases_list)
    for wordtuple in words_list:
        words_dict[wordtuple[0]] = wordtuple[1]
    return words_dict

def gen_links(database_path):
    database = sqlite3.connect(metadict_path(database_path))
    cursor = database.cursor()
    tokens_list = cursor.execute(
            "SELECT filename,tf_idf FROM stories"
            ).fetchall()
    words_dict = words_to_dict(database_path)
    print('Создаются облака ссылок:')
    for n,tokens_tuple in enumerate(tokens_list,1):
        print(n, '/', len(tokens_list), tokens_tuple[0])
        filename = tokens_tuple[0]
        dict_links = {}
        scorecount = 0
        tokens_dict = pickle.loads(tokens_tuple[1])
        scorecount = sum(tokens_dict.values())
        for token,score in tokens_dict.items():
            # Чувствительность настраивается по абсолютому счёту:
            if score >= SCORE_MIN and score < SCORE_MAX:
                percent_score = score / scorecount
                if token in words_dict:
                    #print(token, words_dict[token])
                    # Находим название и делаем ключом словаря:
                    top_filename = words_dict[token]
                    if words_dict[token] not in dict_links:
                        dict_links[top_filename] = percent_score
                    else:
                        dict_links[top_filename] = dict_links[top_filename] + percent_score
        dict_links = pickle.dumps(dict_links)
        cursor.execute("UPDATE stories SET links=? WHERE filename=?", [\
            dict_links,\
            filename,\
            ])
        database.commit()
    database.close()

def select_file(file_path):
    """Определяем тип файла, конвертируем и переносим в базу данных.

    Скрипт умеет распаковывать fb2.zip, парсит fiction_book и читает txt.
    """
    # fb2.zip распаковываем, fb2 парсим, текст исследуем:
    if zipfile.is_zipfile(file_path):
        fb2 = extract_fb2_zip(file_path)
        book_to_database(DATABASE_PATH, file_path, fb2_to_dict(fb2))
    elif os.path.splitext(file_path)[1][1:] == 'fb2':
        fb2 = file_path
        book_to_database(DATABASE_PATH, file_path, fb2_to_dict(fb2))
    else:
        file = open(file_path, "r")
        text = file.read()
        file.close()
        book_to_database(DATABASE_PATH, file_path, txt_to_dict(text))

def read_links(database_path, search_string='', output_max=20):
    """Вывод схожих рассказов таблицей."""
    database = sqlite3.connect(metadict_path(database_path))
    cursor = database.cursor()
    search_string = ' '.join(search_string)
    search_string = '%' + search_string + '%'
    sql_list = cursor.execute(
            "SELECT filename,links FROM stories WHERE filename LIKE ?\
                    OR author LIKE ? OR book_title LIKE ?", [\
            search_string,\
            search_string,\
            search_string,\
            ]).fetchall()
    for n,sql_tuple in enumerate(sql_list,1):
        print('# ----------------------------------------------------------------------------')
        print('# ', n, '/', len(sql_list), sql_tuple[0])
        print('# ----------------------------------------------------------------------------')
        cloud = pickle.loads(sql_tuple[1])
        cloud = dict_sort(cloud)
        n = 0
        for name, value in cloud.items():
            book_data = cursor.execute("SELECT book_title,author\
                    FROM stories WHERE filename=? COLLATE NOCASE"\
                    ,(name,)).fetchone()
            book = book_data[0]
            author = book_data[1]
            if book == 'None':
                book = name
            # Вывод в процентах:
            value = round(value * 100, 5)
            if value > 0.1 and n < output_max:
                n = n + 1
                print ('{0:2} {1:10} | {3:30} | {2}'.format(n, round(value, 3),
                    book, author))
                #print(value, book_data[0],book_data[1])

def read_blobs(database_path, search_string='', output_max=20):
    """Вывод ключевых слов таблицей."""
    database = sqlite3.connect(metadict_path(database_path))
    cursor = database.cursor()
    search_string = ' '.join(search_string)
    search_string = '%' + search_string + '%'
    sql_list = cursor.execute(
            "SELECT filename,tf_idf FROM stories WHERE filename LIKE ?\
                    OR author LIKE ? OR book_title LIKE ? COLLATE NOCASE", [\
            search_string,\
            search_string,\
            search_string,\
            ]).fetchall()
    # Исправить. Очень тормозная фигня, лучше filename прямо в облако ссылок прописать.
    authors_dict = gen_authors_dict(database_path)
    for n,sql_tuple in enumerate(sql_list,1):
        print('# ----------------------------------------------------------------------------')
        print('# ', n, '/', len(sql_list), sql_tuple[0])
        print('# ----------------------------------------------------------------------------')
        cloud = pickle.loads(sql_tuple[1])
        cloud = dict_sort(cloud)
        n = 0
        for word, value in cloud.items():
            if n < output_max:
                n = n + 1
                print ('{0:3} {1:10} | {2:30} | {3}'.format(n, round(value),
                    word, authors_dict.get(word)[2]))
            else:
                break

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
        filelist = (pathfinder(BOOKS_DIR))
    
    # Создаём базу данных:
    if os.path.exists(metadict_path(DATABASE_PATH)) is not True:
        create_stories_database(DATABASE_PATH)
    
    # Работаем:
    for n,file_path in enumerate(filelist,1):
        if not filename_in_database(file_path, DATABASE_PATH):
            print(n, '/', len(filelist), file_path)
            regen_words_table = True
            select_file(file_path)
    # Создаём общий список слов:
    if regen_words_table:
        gen_words_table(DATABASE_PATH)
        gen_wordfreq_idf(DATABASE_PATH)
        gen_links(DATABASE_PATH)
    # Вывод данных:
    if namespace.output is True:
        read_blobs(DATABASE_PATH, namespace.search_string, namespace.output_max)
    elif namespace.links is True:
        read_links(DATABASE_PATH, namespace.search_string, namespace.output_max)
