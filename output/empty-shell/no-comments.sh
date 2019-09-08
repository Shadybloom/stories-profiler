#!/bin/bash
# Скрипт создаёт копию редактуры без комментариев, которые '**такие**'
# И без лишних пустых строк.

cd ~/workspace/empty-shell
cat ./пустая-оболочка.txt | grep -v '\*\*.*\*\*' | grep -v '^$' | sed 's/$/\n/' > ./пустая-оболочка-без-комментариев.txt
