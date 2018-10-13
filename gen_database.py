#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Извлекаем текст, название и автора из fb2, fb2.zip и txt, переносим в базу данных.
# Создаём таблицы частоты слов (с нормализацией) и фраз (разделённых знаками препинания).

import os
import re
import argparse
from lxml import etree
import zipfile
import sqlite3
import wordfreq_morph
from itertools import groupby

#-------------------------------------------------------------------------
# Опции:

BOOK_DIR = 'fb2'
DATABASE_NAME = 'database/stories.sqlite'
# Нормализация слов с помощью pymorphy:
MORPH_NORMALIZATION = False
MORPH_NORMALIZATION_FORCED = False
# Хранить текст не обязательно, достаточно списков:
SAVE_BOOK_TEXT_IN_DATABASE = False
# Минимальное число совпадений фразы для выборки в словарь:
PHRASEFREQ_MIN = 2

#-------------------------------------------------------------------------
# Функции:

def create_parser():
    """Список доступных параметров скрипта."""
    parser = argparse.ArgumentParser()
    parser.add_argument('file',
                        nargs='*',
                        help='Файлы в формате fb2'
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

def zip_fb2_extract (file_path):
    """Извлекает текст (последний файл) из fb2.zip."""
    #if os.path.splitext(file)[1][1:] == 'zip':
    if zipfile.is_zipfile(file_path):
        zip_ref = zipfile.ZipFile(file_path, 'r')
        unzip_fb2 = zip_ref.open(zip_ref.namelist()[-1])
        zip_ref.close()
    return unzip_fb2

def f_date_extract (tree):
    """Пытаемся извлечь дату создания рассказа."""
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
    except:
        date = None
        return date

def f_text_clean (raw_text):
    """Чистим текст от пунктуации и повторяющихся слов."""
    cleant_text = re.findall(r"(\w+)", raw_text, re.UNICODE)
    # Удаляем повторяющиеся элементы в списке (сохраняя порядок):
    cleant_text = [el for el, _ in groupby(cleant_text)]
    cleant_text = ' '.join(cleant_text)
    #cleant_text = '_'.join(cleant_text)
    #cleant_text = cleant_text.lower()
    return cleant_text

def f_phrases_rate (story_phrasefreq_dict, phrasefreq_min=PHRASEFREQ_MIN):
    """Фильтруем фразы по минимальному числу совпадений."""
    phrasefreq_dict_clean = { }
    for phrase,value in story_phrasefreq_dict.items():
        if value >= phrasefreq_min:
            phrasefreq_dict_clean[phrase] = value
    return phrasefreq_dict_clean

def fb2_to_dict (file_path):
    """Создаёт словарь из книги в формате fb2. Название, автор, дата, списки."""
    try:
        tree = etree.parse(file_path)
        #root = tree.getroot()
        fb2_dict = {}
        #fb2_dict['author'] = ' '.join(wordfreq_morph.split_to_words(
        #        ''.join(tree.find(".//{*}author").xpath(".//text()"))))
        fb2_dict['author'] = f_text_clean(''.join(tree.find(".//{*}author").xpath(".//text()")))
        fb2_dict['book_title'] = f_text_clean(''.join(tree.find(".//{*}book-title").xpath(".//text()")))
        fb2_dict['date_added'] = f_date_extract(tree)
        #print(fb2_dict['author'], fb2_dict['book_title'],fb2_dict['date_added'])
        fb2_dict['annotation'] = ' '.join(tree.find(".//{*}annotation").xpath(".//text()"))
        fb2_dict['body_text'] = ' '.join(tree.find(".//{*}body").xpath(".//text()"))
        fb2_dict['wordfreq'] = wordfreq_morph.run( \
                fb2_dict['body_text'], \
                morph_soft=MORPH_NORMALIZATION, \
                morph_forced=MORPH_NORMALIZATION_FORCED)
        fb2_dict['phrasefreq'] = f_phrases_rate(wordfreq_morph.run( \
                fb2_dict['body_text'], \
                phrase=True),
                PHRASEFREQ_MIN)
        fb2_dict['wordcount'] = len(wordfreq_morph.split_to_words( \
                fb2_dict['body_text']))
        fb2_dict['phrasecount'] = len(wordfreq_morph.split_to_phrases( \
                fb2_dict['body_text']))
        fb2_dict['wordfreq_count'] = len(fb2_dict['wordfreq'])
        fb2_dict['phrasefreq_count'] = len(fb2_dict['phrasefreq'])
        #print(fb2_dict['wordcount'], fb2_dict['wordfreq_count'],fb2_dict['phrasefreq_count'])
        return fb2_dict
    except:
        print('Ошибка в fb2_to_dict:', file_path)
        return None

def txt_to_dict (text):
    """Создаёт словарь из куска текста."""
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
            morph_soft=MORPH_NORMALIZATION, \
            morph_forced=MORPH_NORMALIZATION_FORCED)
    txt_dict['phrasefreq'] = f_phrases_rate(wordfreq_morph.run( \
            text, \
            phrase=True),
            PHRASEFREQ_MIN)
    txt_dict['wordcount'] = len(wordfreq_morph.split_to_words(text))
    txt_dict['phrasecount'] = len(wordfreq_morph.split_to_phrases(text))
    txt_dict['wordfreq_count'] = len(txt_dict['wordfreq'])
    txt_dict['phrasefreq_count'] = len(txt_dict['phrasefreq'])
    #print(txt_dict['wordcount'], txt_dict['wordfreq_count'],txt_dict['phrasefreq_count'])
    return txt_dict

def create_stories_database (database_name):
    """База данных с названияим, авторами и текстами рассказов."""
    database = sqlite3.connect(metadict_path(database_name))
    cursor = database.cursor()
    cursor.execute("""CREATE TABLE IF NOT EXISTS stories (
        id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
        filename TEXT NOT NULL,
        author TEXT DEFAULT NULL,
        book_title TEXT DEFAULT NULL,
        date_added TEXT DEFAULT NULL,
        annotation TEXT DEFAULT NULL,
        body_text TEXT DEFAULT NULL,
        wordfreq TEXT DEFAULT NULL,
        phrasefreq TEXT DEFAULT NULL,
        tf_idf TEXT DEFAULT NULL,
        wordcount INTEGER NOT NULL,
        phrasecount INTEGER NOT NULL,
        wordfreq_count INTEGER NOT NULL,
        phrasefreq_count INTEGER NOT NULL
        )""")
    cursor.execute("""CREATE INDEX IF NOT EXISTS index_stories ON stories (
        id,
        filename,
        author,
        book_title,
        date_added,
        annotation,
        body_text,
        wordfreq,
        phrasefreq,
        tf_idf,
        wordcount,
        phrasecount,
        wordfreq_count,
        phrasefreq_count
        )""")
    database.close()
    print("[OK] CREATE",database_name)

def create_words_table(database_name):
    database = sqlite3.connect(metadict_path(database_name))
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

def create_phrases_table(database_name):
    database = sqlite3.connect(metadict_path(database_name))
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

def book_to_database (database_name, file_path, fb2_dict):
    """Словарь книги переносится в базу данных."""
    # Создаётся база данных, если её нет:
    if os.path.exists(metadict_path(database_name)) is not True:
        create_stories_database(database_name)
    # Проверка, сработал ли парсер:
    if not fb2_dict:
        return None
    # Подключается база данных:
    database = sqlite3.connect(metadict_path(database_name))
    cursor = database.cursor()
    # Элементы словаря в переменные:
    filename = str(os.path.basename(file_path))
    author = str(fb2_dict.get('author'))
    book_title = str(fb2_dict.get('book_title'))
    date_added = str(fb2_dict.get('date_added'))
    annotation = str(fb2_dict.get('annotation'))
    if SAVE_BOOK_TEXT_IN_DATABASE is True:
        body_text = str(fb2_dict.get('body_text'))
    else:
        body_text = None
    wordfreq = str(fb2_dict.get('wordfreq'))
    phrasefreq = str(fb2_dict.get('phrasefreq'))
    tf_idf = fb2_dict.get('tf_idf')
    wordcount = int(fb2_dict.get('wordcount'))
    phrasecount = int(fb2_dict.get('phrasecount'))
    wordfreq_count = int(fb2_dict.get('wordfreq_count'))
    phrasefreq_count = int(fb2_dict.get('phrasefreq_count'))
    #print(book_title,filename,date_added)
    # Переменные в базу данных:
    cursor.execute("INSERT INTO stories VALUES(NULL,?,?,?,?,?,?,?,?,?,?,?,?,?)", [\
        filename,\
        author,\
        book_title,\
        date_added,\
        annotation,\
        body_text,\
        wordfreq,\
        phrasefreq,\
        tf_idf,\
        wordcount,\
        phrasecount,\
        wordfreq_count,\
        phrasefreq_count,\
        ])
    database.commit()
    database.close()

def filename_in_database (file_path, database_name=DATABASE_NAME):
    """Проверка, есть ли название в базе данных."""
    database = sqlite3.connect(metadict_path(database_name))
    filename = os.path.basename(file_path)
    cursor = database.cursor()
    filename_test = cursor.execute("SELECT filename FROM stories WHERE filename=?"\
            ,(filename,)).fetchall()
    return filename_test

def fill_words_dict(words_all_dict, story_wordfreq_dict, story_tuple):
    """Общий словарь заполняется словами из словарей рассказов.

    Если слово уже есть, частота суммируется, а к числу совпадений добавляется единица.
    Если в новом рассказе слово встречается чаще, тогда этот рассказ ассоциируется со словом.
    Частота слова в процентах от текста рассказа.
    """
    filename, book_title, author, wordcount = story_tuple[0:4]
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
            if word_percent >= words_all_dict[word][2]:
                # Если в новой книге чаще встречается слово, значит её в топ:
                words_all_dict[word] = [wordfreq_new, storycount, word_percent,
                        filename, book_title, author]
            else:
                words_all_dict[word][0:2] = wordfreq_new, storycount
    return words_all_dict

def fill_words_table(database_name):
    """Создаём текстовый корпус. Самые распространённые слова в текстах."""
    words_all_dict = {}
    phrases_all_dict = {}
    database = sqlite3.connect(metadict_path(database_name))
    cursor = database.cursor()
    stories_list = cursor.execute(
            "SELECT filename,book_title,author,\
            wordcount,phrasecount,wordfreq,phrasefreq FROM stories"
            ).fetchall()
    create_words_table(database_name)
    create_phrases_table(database_name)
    print('Создаётся текстовый корпус:')
    for n,story_tuple in enumerate(stories_list,1):
        print(n, '/', len(stories_list), story_tuple[0])
        # Берём переменные из базы данных:
        story_wordfreq_dict = eval(story_tuple[5])
        story_phrasefreq_dict = eval(story_tuple[6])
        # По очереди перебираем слова из списка рассказа:
        fill_words_dict(words_all_dict, story_wordfreq_dict, story_tuple)
        fill_words_dict(phrases_all_dict, story_phrasefreq_dict, story_tuple)
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

def select_file(file_path):
    """Определяем тип файла, конвертируем и переносим в базу данных.

    Скрипт умеет распаковывать fb2.zip, парсит fiction_book и читает txt.
    """
    # fb2.zip распаковываем, fb2 парсим, текст исследуем:
    if zipfile.is_zipfile(file_path):
        fb2 = zip_fb2_extract(file_path)
        book_to_database(DATABASE_NAME, file_path, fb2_to_dict(fb2))
    elif os.path.splitext(file_path)[1][1:] == 'fb2':
        fb2 = file_path
        book_to_database(DATABASE_NAME, file_path, fb2_to_dict(fb2))
    else:
        file = open(file_path, "r")
        text = file.read()
        file.close()
        book_to_database(DATABASE_NAME, file_path, txt_to_dict(text))

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
        filelist = (pathfinder(BOOK_DIR))
    
    # Создаём базу данных:
    if os.path.exists(metadict_path(DATABASE_NAME)) is not True:
        create_stories_database(DATABASE_NAME)
    
    # Работаем:
    for n,file_path in enumerate(filelist,1):
        print(n, '/', len(filelist), file_path)
        if not filename_in_database(file_path, DATABASE_NAME):
            select_file(file_path)
    # Создаём общий список слов:
    fill_words_table(DATABASE_NAME)
