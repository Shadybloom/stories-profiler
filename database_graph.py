#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Скрипт создаёт граф связей между текстами в базе данных.

import os
import sqlite3
import graphviz
import argparse
import pickle
import time
from math import log

from profiler_config import *
from gen_database import script_path
from gen_database import correct_path
from gen_database import dict_sort

#-------------------------------------------------------------------------
# Опции:

graph_engine = 'twopi'
graph_output = 'png'
graph_conf = {
        'splines':'true',
        'spines':'spline',
        'concentrate':'true',
        'overlap':'scale',
        'mindist':'2.5',
        'ranksep':'1',
        'nodesep':'1',
        'ratio':'auto',
        }
node_conf = {
        'shape':'hexagon',
        'style':'filled',
        #'fixedsize':'True',
        #'penwidth':'0.5',
        #'width':'2',
        }
edge_conf = {
        'arrowsize':'0.5',
        'arrowshape':'vee',
        }

#-------------------------------------------------------------------------
# Функции:

def create_parser():
    """Список доступных параметров скрипта."""
    parser = argparse.ArgumentParser()
    parser.add_argument('search_string',
                        action='store', type=str, nargs='*', default='',
                        help='Поиск в базе данных (Янтарь, Янт, yantar)'
                        )
    parser.add_argument('-c' '--cycles',
                        action='store', dest='cycles', type=int, default=RECURSION_LVL,
                        help='Глубина исследования (1-10).'
                        )
    parser.add_argument('-s' '--sense',
                        action='store', dest='sense', type=int, default=SIMILARITY_MAX,
                        help='Чувствительность сенсора (1-1000).'
                        )
    parser.add_argument('-n' '--nodes',
                        action='store', dest='nodes', type=int, default=NODES_MAX,
                        help='Число нод в выводе (1-100)'
                        )
    parser.add_argument('-o', '--output',
                        action='store_true', default='False',
                        help='Выводить только имя созданного файла'
                        )
    parser.add_argument('-D', '--database',
                        action='store', dest='database', type=str, default=DATABASE_PATH,
                        help='Путь к другой базе данных'
                        )
    return parser

def ordered_uniq(seq, idfun=None): 
   # order preserving
   # https://www.peterbe.com/plog/uniqifiers-benchmark
   if idfun is None:
       def idfun(x): return x
   seen = {}
   result = []
   for item in seq:
       marker = idfun(item)
       # in old Python versions:
       # if seen.has_key(marker)
       # but in new ones:
       if marker in seen: continue
       seen[marker] = 1
       result.append(item)
   return result

def get_graph(search_list, cursor):
    """Поисковые запросы к базе данных, принимает список, ищет по строкам.
    
    Одиночный поисковый запрос -- от человека (ищется повсюду)
    Группа поисковых запросов -- от машины (ищется по точному соответствию файлов)
    """
    blob_list = [ ]
    for n,search_string in enumerate(search_list):
        # Единственный поисковый запрос -- от человека
        if len(search_list) == 1:
            sql_query = "SELECT filename, book_title, author, wordcount, links\
                    FROM stories WHERE filename LIKE '%{s}%' \
                    OR author LIKE '%{s}%' OR book_title LIKE '%{s}%'" \
                    .format(s=search_string)
        # Группа поисковых запросов -- от машины
        else:
            sql_query = "SELECT filename, book_title, author, wordcount, links\
                    FROM stories WHERE filename='{s}'".format(s=search_string)
        blob_list += cursor.execute(sql_query).fetchall()
        #print ('{0:4} {1:10}'.format(n, search_string))
    return blob_list

def clear_linkscloud(linkscloud, similarity_max=SIMILARITY_MAX, similarity_score=SIMILARITY_SCORE_MIN):
    """Фильтруем облако ссылок, ограничение по рейтингу соответствия и количеству элементов."""
    linkscloud_clear = {}
    n = 0
    for key, el in dict_sort(linkscloud).items():
        score = el * 100
        if score > similarity_score and n < similarity_max:
            linkscloud_clear[key] = el
            n += 1
    return linkscloud_clear

def read_graph(search_string, database_path,
        recurion_lvl=RECURSION_LVL, sense=SIMILARITY_MAX, nodes_max=NODES_MAX, suppress_output=False):
    """Рекурсивно читаем словари ссылок и создаём срез графа связей.
    
    В вывод попадают только связанные с поисковым запросом вершины графа.
    Например, если у нас в запросе автор "В облаках пушистых лапки"
    Тогда каждый текст в выдаче должен будет ссылаться на
    "Янтарь в темноте", "Город на цепи" и "Soldiers of the Dark Ages"
    Это главная фича, что позволяет отсеивать чужие работы.
    И обнаруживать рассказы, написанные под псевдонимом.
    """
    graph_list = []
    database = sqlite3.connect(database_path)
    cursor = database.cursor()
    search_string = ' '.join(search_string)
    # Первым в списке оказывается наш поисковый запрос.
    search_list = [search_string]
    # Рекурсивный обход графа, пока число собранных нод не достигнет предела:
    sql_list = get_graph(search_list, cursor)
    # Результаты поиска, выводятся только ноды, ссылающиеся на них:
    test_list = [el[0] for el in sql_list]
    cycle = 0
    while len(graph_list) < nodes_max and cycle < recurion_lvl:
        cycle += 1
        sql_list = get_graph(search_list, cursor)
        # Начинаем обрабатывать найденные кортежи:
        for sql_tuple in sql_list:
            nametuple = sql_tuple[0:4]
            # Чистим облако ссылок и добавляем в основной словарь:
            if len(graph_list) < nodes_max:
                linkscloud_raw = pickle.loads(sql_tuple[4])
                linkscloud = clear_linkscloud(linkscloud_raw, sense)
                # Извлекаем ссылки для следующих циклов поиска:
                links_list = [key for key in linkscloud.keys()]
                # Проверяем, ссылается ли нода на результаты первого запроса:
                for link in links_list:
                    if link in test_list:
                        search_list.extend(links_list)
                        out_tuple = nametuple, linkscloud
                        graph_list.append(out_tuple)
                        break
            else:
                break
        # Чистим поисковый список (без ломающего порядок set)
        # Функция ordered_uniq чистит список от дубликатов, сохраняя порядок.
        # Затем мы создаём срез первого списка без элементов второго.
        search_list = ordered_uniq(search_list)
        reject_list = [el[0][0] for el in graph_list]
        search_list = [el for el in search_list if el not in reject_list]
        # Ввыводим данные по ходу работы:
        if suppress_output is not True:
            print('CYCLE: {0} / {1} {2:60} | {3:10} KEYS'.format(
                cycle, recurion_lvl, ' '.join(test_list), len(graph_list)))
    return graph_list

def format_namestring(nametuple):
    """Форматируем строку вывода."""
    filename, book_title, author, wordcount = nametuple
    if book_title == 'None':
        book_title = filename
    if author == 'None':
        author = 'Unknown'
    namestring = "{0}\n{1}\n{2} words".format(author, book_title, wordcount)
    return namestring

def format_connects(value, score=SIMILARITY_SCORE_MIN):
    """Упрощаем веса связей, чтобы в выводе не было слишком больших/мелких срелок."""
    # Исправить.
    # Какой же уродливый хардкод. Нужна хитрая функция, чобы и пики снижать и минимуму поднимать.
    value = round(value * 1000 * 2, 5)
    if value > 100:
        return 30
    if value > 50:
        return 25
    if value > 20:
        return 20
    elif value < 2:
        return 2
    else:
        return value

def graphviz_output(graph_list):
    # Исправить.
    # Это большая функция, раздели.
    # Для начала создаём проект и подключаем опции graphviz:
    dot = graphviz.Digraph(\
            format=graph_output, engine=graph_engine, graph_attr=graph_conf,\
            node_attr=node_conf, edge_attr=edge_conf,\
            )
    # Вычисляем количество всех постов по wordcount текстов:
    wordcount_all = sum(nametuple[0][3] for nametuple in graph_list)
    storycount = len(graph_list)
    wordcount_medial = wordcount_all / storycount
    files_list = [el[0][0] for el in graph_list]
    # Создаём ноды, поочерёдно перебирая неймфагов из словаря:
    hsv_color = 0
    for outtuple in graph_list:
        nametuple = outtuple[0]
        filename, book_title, author, wordcount = nametuple[0:4]
        node_name = filename
        label = format_namestring(nametuple)
        # Толщина обводки, текста и размер ноды -- относительное число постов:
        node_strength = str(wordcount / wordcount_medial * 2)
        font_strength = str(log(wordcount / storycount) * 2)
        # Цвет в формате HSV, шаг зависит от числа неймфагов в словаре:
        hsv_color = round(hsv_color + 1 / storycount,4)
        hsv_border = str(hsv_color)+','+'1'+','+'1'
        # Насыщенность цвета зависит от числа постов, меньше -- бледнее:
        hsv_saturation = str(wordcount / wordcount_all * 3)
        hsv_fill = str(hsv_color)+','+str(hsv_saturation)+','+'1'
        # Создаём вершину графа
        dot.node(node_name, label, color=hsv_border, fillcolor=hsv_fill, fontsize=font_strength,
                width=node_strength, penwidth=node_strength)
    # Создаём линии связей, поочерёдно перебирая друзей каждого неймфага:
    hsv_color = 0
    for outtuple in graph_list:
        nametuple = outtuple[0]
        linkscloud = outtuple[1]
        filename, book_title, author, wordcount = nametuple[0:4]
        # Опять же, насыщенность цвета зависит от числа постов:
        hsv_color = round(hsv_color + 1 / storycount,4)
        hsv_saturation = str(wordcount / wordcount_all * 3)
        hsv = str(hsv_color)+','+hsv_saturation+','+'1'
        node_name = filename
        #print(hsv)
        for friend, score in linkscloud.items():
            # Отбрасываем ссылки на ноды вне выборки и ссылки нод на самих себя:
            if friend in files_list and not friend == filename:
                for key in files_list:
                    if key == friend:
                        friend_name = friend
                        connect_value = str(format_connects(score))
                        #connect_value = str(round(score * 1000 * 2, 5))
                        dot.edge(node_name, friend_name, color=hsv, penwidth=connect_value)
    # Вывод данных в формате dot:
    #print(dot.source)
    # Имя файла -- юникстайм (как на бордах)
    img_path = script_path(IMG_DIR) + '/' + str(round(time.time() * 10000))
    # Генерация схемы:
    print(dot.render(filename=img_path))

#-------------------------------------------------------------------------
# Тело программы:

if __name__ == '__main__':
    # Создаётся список аргументов скрипта:
    parser = create_parser()
    namespace = parser.parse_args()
    # Уточняем пути к базе данных и основному словарю:
    database_path, tokens_path = correct_path(namespace.database)
    # Создаём список с графом связей:
    graph_list = read_graph(namespace.search_string, database_path,
            namespace.cycles, namespace.sense, namespace.nodes, namespace.output)
    # Выводим данные с помощью graphviz:
    graphviz_output(graph_list)
