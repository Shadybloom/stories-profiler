#!/bin/bash
# Скрипт преобразует fb2 в txt.

for file in ./fb2/*
do
    filename=`echo "$file" | egrep -o "[^/]+$"`
    text=`cat $file | sed "s#<p>#<p>\n#gi" | sed "s#<.*>##gi"`
    echo "$text" > ./txt/$filename.txt
    # Вывод на терминал:
    echo "./txt/$filename.txt"
done
