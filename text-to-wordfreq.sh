#!/bin/bash
# Скрипт создаёт частотные словари из текстов в ./txt/
# Используется wordfreq-morph.py

for file in ./txt/*
do
    filename=`echo "$file" | egrep -o "[^/]+$" | egrep -o "^[^.]+"`
    python ./wordfreq-morph.py -m $file > ./words/$filename.list
    # Вывод на терминал:
    echo "./words/$filename.list"
done
