#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Загружает текст рассказа с samlib.ru, создаёт из него упрощённый fb2.
# Для дальнейшей обработки gen_database, чтобы название/имя_автора не терять.

import argparse
from lxml import html
from lxml import etree
import requests
from bs4 import BeautifulSoup

#-------------------------------------------------------------------------
# Функции:

def create_parser():
    """Список доступных параметров скрипта."""
    parser = argparse.ArgumentParser()
    parser.add_argument('url',
                        nargs=1,
                        help='страница автора/поиска samlib.ru'
                        )
    return parser

#-------------------------------------------------------------------------
# Тело программы:

if __name__ == '__main__':
    parser = create_parser()
    namespace = parser.parse_args()

    # Загружаем страницу:
    url = namespace.url[0]
    page = requests.get(url).text

    # Парсим древо тегов:
    tree = html.fromstring(page, parser=etree.HTMLParser(recover=True))
    # Имя автора идёт первым на странице в теге заголовка <h3></h3>, других указателей нет.
    # После имени автора стоит символ новой строки и двоеточая, которые убираем:
    author = tree.findall(".//{*}h3")[0].xpath(".//text()")[0]
    author = author[:-2]
    # Название книги тоже выделено заголовком:
    book_title = tree.findall(".//{*}h2")[0].xpath(".//text()")[0]
    
    # Самое простое и самое мусорное решение:
    soup = BeautifulSoup(page, 'lxml')
    body_text = soup.get_text()

    # Текст в теге <xxx7>
    # Не всегда!
    #soup = BeautifulSoup(page, 'lxml')
    #soup = soup.find_all('xxx7')
    #body_text = soup[0].get_text()

    # Текст рассказа между тегами параграфов <dd></dd>
    # А вот и нет, фигня получается.
    #soup = BeautifulSoup(page, 'lxml')
    #body_text = ''
    #for el in soup.findAll('dd'):
    #    body_text = body_text + el.contents[0]

    # Текст в теге <div align="justify">
    # А вот и нет, не везде! Да как же достало.
    #soup = BeautifulSoup(page, 'lxml')
    #soup = soup.find_all(attrs={'align' : 'justify'})
    #body_text = soup[0].get_text()    

    # Создаём упрощённый fb2
    fb2 = """<?xml version='1.0' encoding='UTF-8'?>
    <FictionBook xmlns:xlink="http://www.w3.org/1999/xlink" xmlns="http://www.gribuser.ru/xml/fictionbook/2.0">
    <description>
    <title-info>
    <author>{0}</author>
    <book-title>{1}</book-title>
    <annotation>
    </annotation>
    <lang>ru</lang>
    </title-info>
    <document-info>
    <author>{0}</author>
    <date></date>
    <id/>
    <version>2.0</version>
    </document-info>
    </description>
    <body>
    {2}
    </body>
    </FictionBook>
    """.format(author, book_title, body_text)
    print(fb2)
